#!/usr/bin/env python3
"""Generation-specificity audit (#4007): deterministic, offline, stdlib + PyYAML.

Finds text and code in the D4D generation process that is specific to a
Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program
(tracked) or to biomedical/clinical data (tracked), and reports what "api"
means in the code: one monolithic call or several phases, and whether any
step of an API run is agentic.

    python .claude/skills/d4d-generation-specificity-audit/scan.py \
        --report notes/x.md --json notes/x.json

Exit status: 0 when no gating approach counts a gc_project hit outside an
exception (model-facing text, or a code branch or table, under the file's
role in that approach); 1 when one does; 2 when the scan did not happen:
PyYAML cannot be imported, the self-test failed, the
configuration is malformed, a discovered surface could not be read, a
derivation the report rests on found nothing ("not derived"), or the scan
stopped on an error. A crash is never exit 1, which means violations (#4027,
#4058).

Nothing here imports the project package: the runner's tables are read with
`ast`, so the audit runs from any checkout without the project's own
dependencies and never executes generation code. It does need PyYAML.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import fnmatch
import io
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import tokenize
import traceback
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    # An uncaught ImportError exits 1, the status that means violations: a
    # missing dependency is a scan that did not happen (#4058).
    print("scan failed (exit 2, the scan did not happen): PyYAML cannot be imported by "
          f"{sys.executable}; run the scanner with the project's interpreter", file=sys.stderr)
    sys.exit(2)

SKILL_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SKILL_DIR.parents[2]
TOKENS_FILE = SKILL_DIR / "tokens.yaml"
EXCEPTIONS_FILE = SKILL_DIR / "exceptions.yaml"
NEUTRALITY_TEST = "tests/test_neutral_generation_schema.py"
RUNNER = "src/data_sheets_schema/api_runner.py"
CLI_API = "src/data_sheets_schema/cli/api.py"
AGENTIC_RUNTIME = "src/data_sheets_schema/agentic_runtime.py"
DOWNLOAD_GROUP = "src/data_sheets_schema/cli/download.py"
PLAYBOOK = ".claude/commands/d4d-full-core.md"
CATEGORIES = ("gc_project", "bridge2ai_program", "biomedical_clinical")
TRACKED = ("bridge2ai_program", "biomedical_clinical")
#: The trees whose Python modules discovery reads: model clients, run
#: controllers and launchers are found in all three (#4023, #4054).
PYTHON_ROOTS = ("src", "notes", "scripts")

APPROACHES = {
    # name: (gates the exit status, description)
    "native_agentic": (True, "Claude Code / native runtime following the d4d playbooks, the agents they name and the "
                             "files they name"),
    "interactive_session": (True, "a person's Claude Code session in a checkout, where the /d4d-* playbooks run "
                                  "interactively: the project memory (CLAUDE.md), the settings hooks and the "
                                  "descriptions of every command, agent and skill Claude Code loads into it. A "
                                  "registered native launch not shown to pass --safe-mode may load them too (with "
                                  "--bare alone, the descriptions; see run_controllers)"),
    "api": (True, "d4d api run|batch: api_runner and its condition prompts"),
    "github_assistant": (True, "the @d4dassistant workflow, what it names or runs, the condition its d4d api run "
                               "runs, and an instruction file only where the workflow loads one"),
    "shared_schema": (True, "the LinkML generation schema, digest inputs, profile and manifest"),
    "deterministic": (True, "the arm commands that build a non-baseline arm's bundle or record (healthsheet, "
                            "RO-Crate) and their import closure"),
    "run_controllers": (True, "registered-run controllers under notes/ and launchers under scripts/ or src/ that "
                              "build or launch a generation request, the modules they import and the launchers "
                              "that run them"),
    "legacy_monolithic": (True, "generators outside the runner that call a model client to write a D4D record, "
                                "the pre-runner helper scripts and their prompt sets"),
    "shared_input": (False, "the upstream input steps the `d4d download` group imports (download, preprocess, "
                            "concatenate): upstream of every approach"),
    "other_model_client": (False, "reaches a model outside generation: diagnostic probes, evaluators and "
                                  "evaluation controllers, non-D4D extractors. Listed, never gates; a model client "
                                  "a generation closure imports is that approach's surface instead"),
}

#: Modules whose text reaches a model (prompt assembly, bundle text, digest).
#: A hand-kept list: which modules belong to each closure is derived from
#: imports; whether a module *writes model-facing text* is not derivable
#: from an import graph. tests/test_generation_specificity_skill.py fails
#: when a name here is in none of the api, native or deterministic closures.
MODEL_FACING_MODULES = frozenset({
    "api_runner", "schema_digest", "schema_semantics", "source_review", "grounding",
    "scope", "source_priority", "source_metadata", "chunking", "evidence_assertions",
    "agentic_runtime", "audit_batch_context", "audit_batch_format", "audit_grammar",
    "healthsheet", "rocrate_normalize",
})

#: How strongly an approach reaches a file. Per approach the strongest wins:
#: a file one route names for the model is model-facing in that approach
#: however else it is reached, and "exposed" (available, named by nothing
#: live) never gates (#4054).
ROLE_RANK = {"model_facing": 3, "run_shaping": 2, "exposed": 1}
MODEL_FACING_CONTEXTS = {"string_literal", "prose", "example", "instruction", "frontmatter", "value"}
CODE_CONTEXTS = {"code_branch", "code_table"}
EXAMPLE_MARK = re.compile(r"\be\.g\.|\bexample|\bsuch as\b|\bfor instance\b|\bi\.e\.", re.I)
MODAL = re.compile(r"\b(must|should|never|always|do not|don't|required?|prefer|use|read|write|"
                   r"record|include|omit|state)\b", re.I)
CLAUDE_REF = re.compile(r"\.claude/(?:commands|agents)/[\w.-]+\.md")
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".config", ".py"}
#: A repository file a text names by path (#4054): a file under an
#: instruction or code tree with a text suffix. A templated path
#: (`components/{PROJECT}.md`) names no single file and does not match.
NAMED_PATH = re.compile(r"(?<![\w/.-])(?:\./)?((?:\.claude|\.github|src|scripts|notes)/[\w./-]*?[\w-]"
                        r"\.(?:md|txt|ya?ml|json|config|py|sh))(?![\w/-])")
#: Suffixes of a named file a model reads (instructions, schemas, data);
#: a named `.py`, `.sh` or `.config` is code or configuration that runs.
NAMED_TEXT = frozenset({".md", ".txt", ".yaml", ".yml", ".json"})
#: Project memory a text names. Claude Code loads it into a session; the
#: text that names it does not hand it over (#4054).
MEMORY_NAME = re.compile(r"(?<![\w/.-])(CLAUDE(?:\.local)?\.md)\b")
#: A command that runs the path following it on the same line.
RUN_PREFIX = re.compile(r"(?:\bpython3?|\bpoetry run python3?|\buv run python3?|\bbash|\bsh)\s+(?:-[\w-]+\s+)*$")
#: `python -m dotted.module`.
MODULE_RUN = re.compile(r"(?<![\w-])-m\s+([A-Za-z_]\w*(?:\.\w+)*)")
#: The project memory and settings Claude Code loads into an interactive
#: session in a checkout.
PROJECT_MEMORY = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md")
PROJECT_SETTINGS = (".claude/settings.json", ".claude/settings.local.json")
#: `--safe-mode` starts a run "with all customizations (CLAUDE.md, skills,
#: ..., hooks, ..., custom commands and agents, ...) disabled"; `--bare`
#: skips the settings hooks and CLAUDE.md auto-discovery, but "Skills still
#: resolve via /skill-name" (`claude --help`, 2.1.287). So only `--safe-mode`
#: switches off the command, agent and skill descriptions, and either
#: switches off the memory and the hooks (#4131).
SAFE_MODE = "--safe-mode"
MEMORY_OFF_FLAGS = frozenset({"--safe-mode", "--bare"})
#: Where Claude Code finds the commands, agents and skills whose descriptions
#: it lists in every interactive session (the Agent tool's agent types, the
#: skill and command listing); a body is loaded only when it is invoked
#: (#4091). Commands and agents are found at any depth, skills one level down.
SESSION_DESCRIBED = ((".claude/commands", "**/*.md"), (".claude/agents", "**/*.md"), (".claude/skills", "*/SKILL.md"))
#: The frontmatter keys a session lists (the name and the description).
SESSION_KEYS = ("name", "description")
#: A `d4d <group> <command>`, or `python -m data_sheets_schema.cli <group>
#: <command>`, that a text runs: the CLI group it runs (#4091).
CLI_GROUP_RUN = re.compile(r"(?:(?<![\w/.-])d4d|(?<![\w-])-m\s+data_sheets_schema\.cli)\s+([a-z][\w-]*)\s+[a-z]")
#: The CLI package imports every group: a closure that reaches it stops
#: there, and a group is followed where a text runs it (#4091).
CLI_PACKAGE = ("src/data_sheets_schema/cli/__init__.py", "src/data_sheets_schema/cli/__main__.py")
#: YAML files: a comment in one counts where a text names it for the model to
#: Read, since the Read tool returns it raw (#4091); the digest drops it.
YAML_SUFFIXES = frozenset({".yaml", ".yml"})
#: argv flags whose next element is the system prompt a native runtime is
#: launched with (#4054).
SYSTEM_PROMPT_FLAGS = frozenset({"--system-prompt", "--append-system-prompt"})
#: argv flags whose next element names a file holding that system prompt
#: (`claude --help`, 2.1.287): a launch too (#4131), though the data flow
#: from it would follow a path, not text.
SYSTEM_PROMPT_FILE_FLAGS = frozenset({"--system-prompt-file", "--append-system-prompt-file"})
#: Every flag that makes an argv a registered native launch.
LAUNCH_FLAGS = SYSTEM_PROMPT_FLAGS | SYSTEM_PROMPT_FILE_FLAGS
#: Hook output fields Claude Code shows the model: the reason a PreToolUse
#: hook gives for a denial, and the context a hook adds (#4130).
HOOK_MODEL_FIELDS = frozenset({"permissionDecisionReason", "additionalContext"})
#: String methods whose arguments become part of their result (text flows
#: through them: "".join(parts), text.replace(a, b)).
STR_TEXT_METHODS = frozenset({"join", "replace", "format", "format_map", "strip", "rstrip", "lstrip"})

#: Packages whose import makes a module a model client (#4023).
MODEL_CLIENT_PACKAGES = ("anthropic", "openai", "pydantic_ai", "aurelian")
#: A call that sends a request to a model, matched on the dotted callee
#: (`client.messages.create`, `openai.ChatCompletion.create`, ...).
MODEL_CALL = re.compile(r"(?:^|\.)(?:messages\.(?:create|stream)|chat\.completions\.create|responses\.create|"
                        r"ChatCompletion\.create|Completion\.create)$")
#: An agent object's run (pydantic_ai / aurelian): `d4d_agent.run`, `agent.run_sync`.
AGENT_RUN = re.compile(r"(?:^|\.)\w*agent\.run(?:_sync|_stream)?$", re.I)
#: Names a module uses (as code, never in a comment) to build or render a
#: generation request. A notes/ module that uses one is a generation
#: controller (#4023); an evaluation controller renders a rubric request and
#: uses none of them.
GENERATION_BUILDERS = frozenset({"RunSpec", "build_phase", "phase_instruction", "prompt_body", "resolve_prompt",
                                 "playbook_text", "digest_text", "assembly_digest"})
#: A function in a run controller whose string literals are text a model
#: receives, recognised by its name (render_instruction, render_system,
#: child_system, instruction). Data flow finds the rest (#4054).
MODEL_TEXT_FUNCTION = re.compile(r"^(?!verify_|check_)(?:render_\w+|\w*instruction|\w*_system|\w*prompt\w*)$")
#: A registered byte copy kept as run evidence (notes/<run>/registrations/...,
#: .../files/src/...): frozen, never executed, never a surface.
REGISTERED_COPY = re.compile(r"(?:^|/)registrations/|(?:^|/)files/(?:src|scripts|notes|tests|\.claude)/")
#: A path that says the module evaluates records rather than generating one.
EVALUATION_PATH = re.compile(r"evaluat", re.I)
#: A module outside every closure that names D4D or a datasheet and calls a
#: model client writes a D4D record: a generator outside the runner.
GENERATOR_TEXT = re.compile(r"d4d|datasheet", re.I)
#: Names an argparse namespace usually goes by: `args.render_version` reads
#: an option, `spec.render_version` a spec (#4055).
ARGS_NAMES = frozenset({"args", "arguments", "ns", "namespace", "opts", "options", "parsed"})


class ConfigError(ValueError):
    """The configuration, a surface or a derivation failed: the scan did not
    happen (exit 2)."""


class UnparsedSurface(Exception):
    """A Python surface that does not parse under this interpreter: the scan
    cannot classify its code, so it stops (exit 2) rather than report the file
    as having nothing that gates (#4092)."""

    def __init__(self, path: str, error: BaseException):
        super().__init__(f"{path} ({type(error).__name__}: {error})")
        self.path = path


def _interpreter() -> str:
    return f"{platform.python_implementation()} {platform.python_version()} ({sys.executable})"


def _unparsed(files: list[str]) -> ConfigError:
    return ConfigError(f"{len(files)} Python file(s) cannot be parsed by {_interpreter()}, so the scan cannot "
                       "vouch for them: " + "; ".join(files) + ". Code the project's interpreter parses can need a "
                       "newer Python: run the scanner with the project's interpreter (`poetry run python`) (#4092)")


def _not_derived(what: str, how: str) -> ConfigError:
    return ConfigError(f"api meaning not derived: {what} ({how}). The code that decides it changed "
                       "shape; update the derivation in scan.py rather than reporting a fallback (#4025)")


# --------------------------------------------------------------------------
# tokens


@dataclass(frozen=True)
class Token:
    category: str
    pattern: str
    source: str
    regex: re.Pattern = field(compare=False, hash=False, repr=False)


def _assigned_lists(path: Path, names) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names):
            out[node.targets[0].id] = list(ast.literal_eval(node.value))
    return out


IGNORE: list[re.Pattern] = []


def _compile(pattern, where: str) -> re.Pattern:
    """A malformed regex is a configuration error, never a traceback (#4027)."""
    if not isinstance(pattern, str) or not pattern:
        raise ConfigError(f"{where}: a pattern must be a non-empty string, got {pattern!r}")
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise ConfigError(f"{where}: malformed regex {pattern!r}: {exc}") from exc


def load_tokens(root: Path, tokens_file: Path = TOKENS_FILE) -> list[Token]:
    spec = yaml.safe_load(tokens_file.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ConfigError(f"{tokens_file}: the top level must be a mapping")
    imported = spec.get("imported_lists") or {}
    extensions = spec.get("extensions") or {}
    ignore = spec.get("ignore") or []
    if not isinstance(imported, dict) or not isinstance(extensions, dict) or not isinstance(ignore, list):
        raise ConfigError(f"{tokens_file}: `imported_lists` and `extensions` must be mappings and `ignore` "
                          "a list")
    lists = _assigned_lists(root / NEUTRALITY_TEST, set(imported))
    missing = set(imported) - set(lists)
    if missing:
        raise ConfigError(f"{NEUTRALITY_TEST} no longer defines {sorted(missing)}; "
                          "the audit's token source moved — update tokens.yaml")
    tokens, seen = [], set()

    def add(category, pattern, source):
        if category not in CATEGORIES:
            raise ConfigError(f"unknown token category {category!r} for {pattern!r}")
        if (category, pattern) in seen:
            return
        seen.add((category, pattern))
        tokens.append(Token(category, pattern, source, _compile(pattern, f"token from {source}")))

    for name, category in imported.items():
        for pattern in lists[name]:
            add(category, pattern, f"{NEUTRALITY_TEST}:{name}")
    for category, patterns in extensions.items():
        if patterns is not None and not isinstance(patterns, list):
            raise ConfigError(f"{tokens_file}: extensions.{category} must be a list of patterns")
        for pattern in patterns or []:
            add(category, pattern, "tokens.yaml")
    IGNORE[:] = [_compile(p, "tokens.yaml ignore") for p in ignore]
    return tokens


_ANY: dict[int, tuple] = {}


def _any_token(tokens) -> re.Pattern | None:
    """One alternation of every token, used only as a necessary condition: a
    unit no token can match is skipped without a search per token. Cached
    per token list (the entry holds the list, so its id is not reused)."""
    entry = _ANY.get(id(tokens))
    if entry is not None and entry[0] is tokens:
        return entry[1]
    try:
        # a backreference would renumber inside the alternation: no prefilter then
        combinable = tokens and not any(re.search(r"\\[1-9]|\(\?P=", t.pattern) for t in tokens)
        rx = re.compile("|".join(f"(?:{t.pattern})" for t in tokens), re.IGNORECASE) if combinable else None
    except re.error:
        rx = None                       # a pattern that cannot be combined: search per token
    _ANY[id(tokens)] = (tokens, rx)
    return rx


def match_text(text: str, tokens: list[Token]) -> list[tuple[int, int, Token, str]]:
    """Non-overlapping matches; on overlap the more specific category wins."""
    rx = _any_token(tokens)
    if not tokens or (rx is not None and rx.search(text) is None):
        return []
    chosen: list[tuple[int, int, Token, str]] = []
    ignored = [(m.start(), m.end()) for rx in IGNORE for m in rx.finditer(text)]
    for category in CATEGORIES:
        for tok in tokens:
            if tok.category != category:
                continue
            for m in tok.regex.finditer(text):
                if m.end() == m.start():
                    continue
                if any(m.start() < e and s < m.end() for s, e, _, _ in chosen):
                    continue
                if any(s <= m.start() and m.end() <= e for s, e in ignored):
                    continue
                chosen.append((m.start(), m.end(), tok, m.group(0)))
    return sorted(chosen, key=lambda c: (c[0], c[1]))


# --------------------------------------------------------------------------
# per-file context scanners: each yields (line, context, text-to-match, line-text)


def _bare_token(node) -> bool:
    """A string constant with no whitespace: an identifier, key or setting,
    not a sentence."""
    return (isinstance(node, ast.Constant) and isinstance(node.value, str)
            and bool(node.value) and not re.search(r"\s", node.value))


#: Calls that test a value: every constant argument is a branch
#: (`p.startswith("CHORUS")`, `re.fullmatch("VOICE", p)`, `fnmatch(p,
#: "CM4AI*")`), read on a method or a bare name (#4130).
_TEST_CALLS = frozenset({"startswith", "endswith", "__contains__", "match", "fullmatch", "search", "fnmatch",
                         "fnmatchcase"})


def _table_constants(node):
    """The bare-token constants a value holds when the value is a table, a
    default, a key or an argument (#4024, #4130): a bare token itself, or one
    anywhere inside the expression: a collection, any call's arguments
    (`frozenset({...})`, `Path("data/CHORUS")`, `click.Choice([...])`), an
    `or`/`and` default (`project or "CHORUS"`), an operator (`"data/" +
    "CHORUS"`, `Path("raw") / "CHORUS"`), an f-string's literal parts, a
    conditional expression, a comprehension or a lambda's body. A sentence
    is text, not a table entry, and is never yielded; a compared constant is
    a branch (`_python_units` gives the branch precedence)."""
    if node is None:
        return
    if _bare_token(node):
        yield node
    elif isinstance(node, ast.keyword):
        yield from _table_constants(node.value)
    elif isinstance(node, ast.comprehension):
        yield from _table_constants(node.iter)
        for test in node.ifs:
            yield from _table_constants(test)
    elif isinstance(node, ast.expr):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.expr, ast.keyword, ast.comprehension)):
                yield from _table_constants(child)


def _char_col(line: str, byte_col: int) -> int:
    """`ast` columns are UTF-8 byte offsets; `tokenize` columns are characters."""
    return len(line.encode("utf-8")[:byte_col].decode("utf-8", errors="ignore"))


def _token_lines(tok, value: str) -> list[tuple[int, str]]:
    """(physical line, text) for each line of one STRING token's value."""
    first, last = tok.start[0], tok.end[0]
    pieces = value.split("\n")
    if first == last:                       # escaped newlines on one source line
        return [(first, p) for p in pieces]
    if len(pieces) == last - first + 1:     # a block: one value line per source line
        return [(first + i, p) for i, p in enumerate(pieces)]
    # escapes or backslash continuations make the counts differ: each piece
    # goes on the first source line, at or after the previous one, that holds it
    raw = tok.string.split("\n")
    out, at = [], 0
    for p in pieces:
        probe = p.strip()[:40]
        for j in range(at, len(raw)):
            if probe and probe in raw[j]:
                at = j
                break
        out.append((first + at, p))
    return out


_STRING_TOKEN = re.compile(r"(?is)^([rRuU]?)('''|\"\"\"|'|\")(.*)\2$")


def _token_value(text: str):
    """The str a STRING token spells. A plain or raw literal without escapes
    is its body; anything else (escapes, bytes) goes through literal_eval."""
    m = _STRING_TOKEN.match(text)
    if m and ("r" in m.group(1).lower() or "\\" not in m.group(3)):
        return m.group(3)
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None


#: The tokens of an f-string's literal text (Python 3.12+): its middle parts
#: spell the text, its start and end tokens only delimit it.
_FSTRING_MIDDLE = getattr(tokenize, "FSTRING_MIDDLE", None)
_FSTRING_EDGES = {t for t in (getattr(tokenize, "FSTRING_START", None), getattr(tokenize, "FSTRING_END", None))
                  if t is not None}


def _string_lines(node, toks: list, starts: list, lines: list[str]) -> list[tuple[int, str]] | None:
    """(physical line, text) for each line of a string constant, read from
    the tokens that spell it. Implicit concatenation ("a" "b" across lines)
    folds into one value with no newline, so splitting the value alone
    reports every part at the first line (#4026). An f-string's literal
    text is read from its middle tokens (Python 3.12+), so a part of a
    concatenated f-string is reported on its own line too (#4130). None when
    the tokens found do not spell exactly the constant's value (an f-string
    with escapes, or one an older tokenizer reads as a single token)."""
    def char_pos(lineno, byte_col):
        return (lineno, _char_col(lines[lineno - 1], byte_col) if 0 < lineno <= len(lines) else byte_col)

    lo = bisect.bisect_left(starts, char_pos(node.lineno, node.col_offset))
    end = char_pos(node.end_lineno, node.end_col_offset)
    parts, values = [], []
    for tok in toks[lo:]:
        if tok.start >= end:
            break
        if tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT) or \
                tok.type in _FSTRING_EDGES:
            continue
        if tok.type == _FSTRING_MIDDLE:
            value = tok.string
        elif tok.type == tokenize.STRING:
            value = _token_value(tok.string)
        else:
            return None
        if not isinstance(value, str):
            return None
        values.append(value)
        parts += _token_lines(tok, value)
    if not parts or "".join(values) != node.value:
        return None
    return parts


def _python_units(text: str, tree=None):
    if tree is None:
        # A file that does not parse raises: its code cannot be classified,
        # and a surface the scan cannot classify stops it (#4092).
        tree = ast.parse(text)
    lines = text.splitlines()
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        toks = []
    starts = [t.start for t in toks]
    docstrings, branch, table = set(), set(), set()

    def tabled(value):
        table.update(id(c) for c in _table_constants(value))

    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
        if isinstance(node, ast.Compare):
            branch.update(id(n) for n in ast.walk(node) if isinstance(n, ast.Constant))
        if isinstance(node, ast.match_case):
            branch.update(id(n) for n in ast.walk(node.pattern) if isinstance(n, ast.Constant))
        if isinstance(node, ast.Call) and _attr_or_name(node.func) in _TEST_CALLS:
            # a test of the value: str methods, regex and glob matches (#4130)
            branch.update(id(n) for a in node.args for n in ast.walk(a) if isinstance(n, ast.Constant))
        if isinstance(node, ast.Dict):
            table.update(id(k) for k in node.keys if isinstance(k, ast.Constant))
            # a bare-token value is configuration ({"profile": "bridge2ai"}),
            # a value with spaces is text and stays a string literal
            table.update(id(v) for v in node.values if _bare_token(v))
        # Tables, defaults, keys and arguments, at any depth and in any file
        # (#4024, #4130): assignments (module constants, function locals,
        # attributes), loop and comprehension iterables, every keyword and
        # positional argument of every call (`argv.append("AI_READI")`,
        # `run("CHORUS")`, a decorator's `click.Choice([...])`), parameter
        # defaults, returned and yielded values, subscript keys. Each value is
        # read whole: an `or` default, a wrapped value (`Path(...)`, an
        # f-string, a `+` join) and a collection hold table entries too.
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            tabled(node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            tabled(node.iter)
        elif isinstance(node, ast.keyword):
            tabled(node.value)          # project="CHORUS", default="CHORUS", choices=["CM4AI"]
        elif isinstance(node, ast.arguments):
            for d in list(node.defaults) + [d for d in node.kw_defaults if d is not None]:
                tabled(d)
        elif isinstance(node, (ast.Return, ast.Yield, ast.YieldFrom)):
            tabled(node.value)
        elif isinstance(node, ast.Subscript):
            tabled(node.slice)          # CASES["AI_READI"]
        elif isinstance(node, ast.Call):
            for a in node.args:         # d.get(p, "A"), Path("x/CHORUS"), argv.extend(["VOICE"])
                tabled(a)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        context = ("docstring" if id(node) in docstrings else "code_branch" if id(node) in branch
                   else "code_table" if id(node) in table else "string_literal")
        parts = _string_lines(node, toks, starts, lines) if toks else None
        if parts is None:
            # an f-string part: one unit per line of the value from its start
            parts = [(node.lineno + offset if node.end_lineno != node.lineno else node.lineno, part)
                     for offset, part in enumerate(node.value.split("\n"))]
        for lineno, part in parts:
            src = lines[lineno - 1] if 0 < lineno <= len(lines) else part
            yield lineno, context, part, src
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            yield tok.start[0], "comment", tok.string, lines[tok.start[0] - 1]


def _main_blocks(tree) -> list[ast.If]:
    """A module's top-level `if __name__ == "__main__":` blocks: they run
    only when the file is executed as a script (#4054)."""
    if tree is None:
        return []
    out = []
    for node in tree.body:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 \
                and isinstance(node.test.ops[0], ast.Eq):
            sides = {_attr_or_name(node.test.left), getattr(node.test.left, "value", None),
                     _attr_or_name(node.test.comparators[0]), getattr(node.test.comparators[0], "value", None)}
            if {"__name__", "__main__"} <= sides:
                out.append(node)
    return out


def _main_block_lines(tree) -> list[tuple[int, int]]:
    """The lines of a module's top-level `if __name__ == "__main__":` blocks."""
    return [(node.lineno, node.end_lineno) for node in _main_blocks(tree)]


def _markdown_units(text: str, prompt_header: bool):
    lines = text.splitlines()
    header_end = 0
    if prompt_header:
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("## Prompt body"):
                header_end = i
                break
    fence = False
    front = bool(lines) and lines[0].strip() == "---"
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if front and i > 1 and stripped == "---":
            front = False
            yield i, "frontmatter", line, line
            continue
        if stripped.startswith(("```", "~~~")):
            fence = not fence
            yield i, "example", line, line
            continue
        if i <= header_end:
            context = "header"
        elif front:
            context = "frontmatter"
        elif fence or EXAMPLE_MARK.search(line):
            context = "example"
        elif MODAL.search(line):
            context = "instruction"
        else:
            context = "prose"
        yield i, context, line, line


_KEY = re.compile(r"^(\s*)(?:-\s+)?([\w:.$@'\"-]+)\s*:(\s|$)")
_PROSE_KEYS = {"description", "title", "comments", "comment", "note", "notes", "reason", "help"}
_EXAMPLE_KEYS = {"examples", "example", "d4d:docexample", "docexample", "annotations"}
#: Keys whose children are named elements: a slot, class, enum or value
#: *named* `examples` is a name, not the LinkML `examples` metaslot (#4056).
_NAME_CONTAINERS = {"attributes", "slots", "slot_usage", "classes", "enums", "types", "subsets",
                    "permissible_values", "prefixes"}


def _yaml_units(text: str):
    stack: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            yield i, "comment", line, line
            continue
        indent = len(line) - len(line.lstrip(" "))
        body, comment = line, ""
        hash_at = re.search(r"\s#\s", line)
        if hash_at and line.count('"', 0, hash_at.start()) % 2 == 0 and \
                line.count("'", 0, hash_at.start()) % 2 == 0:
            body, comment = line[:hash_at.start()], line[hash_at.start():]
        m = _KEY.match(body)
        if m:
            key_indent = len(m.group(1)) + (2 if body.lstrip().startswith("- ") else 0)
            while stack and stack[-1][0] >= key_indent:
                stack.pop()
            stack.append((key_indent, m.group(2).strip("'\"").lower()))
        else:
            while stack and stack[-1][0] > indent:
                stack.pop()
        keys = [k for _, k in stack]
        # a key directly under a container of named elements is a name: a
        # slot *named* `examples` or `description` is not the metaslot (#4056)
        meta = [not (n and keys[n - 1] in _NAME_CONTAINERS) for n in range(len(keys))]
        if any(k in _EXAMPLE_KEYS and meta[n] for n, k in enumerate(keys)):
            context = "example"
        elif keys and keys[-1] in _PROSE_KEYS and meta[-1]:
            # only the governing key decides: a slot *named* `title` is not prose
            context = "prose"
        else:
            context = "value"
        yield i, context, body, line
        if comment:
            yield i, "comment", comment, line


# ---- code in run-shaping YAML, workflow, config and shell files (#4091)
#
# A workflow, a config or a shell script decides what runs as surely as
# Python does: an `if:` on a project name, a `case` on it, a `--project
# CHORUS` default or a per-project key is project-keyed code. Each line is
# split into spans: a branch (code_branch), a default, assignment, option
# value or bare key/value (code_table), a comment, and the rest of the line,
# which keeps its YAML context or `value`. A token is matched in one span
# only.


def _merge(first: list, more: list) -> list:
    """`first` plus each span of `more` that overlaps none of them."""
    out = list(first)
    for a, b, ctx in more:
        if a < b and not any(a < e and s < b for s, e, _ in out):
            out.append((a, b, ctx))
    return out


def _split_units(line: str, spans: list, rest: str) -> list[tuple[str, str]]:
    """(text, context) for each span of a line, and the line with the spans
    blanked out as `rest`, so that no token is counted twice."""
    out = [(line[a:b], ctx) for a, b, ctx in sorted(spans)]
    chars = list(line)
    for a, b, _ in spans:
        chars[a:b] = " " * (b - a)
    remainder = "".join(chars)
    if remainder.strip():
        out.append((remainder, rest))
    return out


def _unquote(s: str) -> str:
    return re.sub(r"""'([^']*)'|"((?:[^"\\]|\\.)*)"|\\(.)""",
                  lambda m: next(g for g in m.groups() if g is not None), s)


#: A shell token: a separator, a word (quoted parts, escapes and plain text
#: run together), a redirection, or whitespace.
_SH_LEX = re.compile(r"""(?P<sep>;;|&&|\|\||[;&|()])"""
                     r"""|(?P<word>(?:'[^']*'|"(?:[^"\\]|\\.)*"|\\.|[^\s;&|()<>'"\\])+)"""
                     r"""|(?P<redir>\d*[<>]+&?-?)|(?P<space>\s+)|(?P<other>.)""")
_SH_KEYWORDS = frozenset({"if", "elif", "while", "until", "then", "do", "else", "!", "time", "{", "}"})
_SH_DECLARE = frozenset({"export", "local", "readonly", "declare", "typeset"})
_SH_TEST_OPS = frozenset({"=", "==", "!=", "=~", "<", ">", "!", "]", "]]"})


def _sh_literal(word: str) -> str:
    """The literal text a shell word spells: GitHub expressions, shell
    expansions and quotes removed."""
    w = re.sub(r"\$\{\{.*?\}\}", "", word)
    w = re.sub(r"\$(?:\{[^}]*\}|\([^)]*\)?|[A-Za-z_]\w*|[@*#?$!0-9-])|\$$", "", w)
    return _unquote(w)


def _sh_value(word: str) -> bool:
    """A value with literal text and no whitespace: a table entry."""
    lit = _sh_literal(word)
    return bool(lit.strip()) and not re.search(r"\s", lit)


def _sh_operand(word: str) -> bool:
    """A value a test compares or a condition passes: literal text, not an
    operator or an option."""
    return word not in _SH_TEST_OPS and not word.startswith("-") and bool(_sh_literal(word).strip())


class _ShellSpans:
    """Code spans of shell lines, read in order with the state a `case` and a
    multi-line condition need (#4091). A branch: the operands of `[ ]`, `[[
    ]]` and `test`, the arguments of an `if`/`elif`/`while`/`until`
    condition, a `case` pattern. A table: a default (`${VAR:-X}`), an
    assignment (`VAR=X`, `VAR=(X Y)`), a long option's value (`--project X`,
    `--project=X`) and a `for` list, when the value has no whitespace."""

    def __init__(self):
        self.case = 0
        self.pattern_next = False
        self.condition = False

    def __call__(self, line: str) -> list:
        spans: list = []

        def claim(a, b, ctx):
            if a < b and not any(a < e and s < b for s, e, _ in spans):
                spans.append((a, b, ctx))

        # a GitHub expression is substituted before the shell runs: read it as
        # one expansion (its own literals are `_expr_spans`' business)
        line = _GH_EXPR.sub(lambda x: "$" + "_" * (len(x.group(0)) - 1), line)
        toks = []
        for m in _SH_LEX.finditer(line):
            kind, text = m.lastgroup, m.group(0)
            if kind == "space":
                continue
            if kind == "word" and text.startswith("#") and (m.start() == 0 or line[m.start() - 1].isspace()
                                                            or (toks and toks[-1][0] == "sep")):
                claim(m.start(), len(line), "comment")
                break
            toks.append((kind, m.start(), m.end(), text))
        code_end = spans[0][0] if spans else len(line)
        for m in re.finditer(r"\$\{[A-Za-z_]\w*:?[-=+]((?:[^{}]|\{[^{}]*\})*)\}", line[:code_end]):
            if _sh_literal(m.group(1)).strip():
                claim(m.start(1), m.end(1), "code_table")
        start = 0
        if self.case and self.pattern_next:
            close = next((k for k, t in enumerate(toks) if t[0] == "sep" and t[3] == ")"), None)
            if close is not None and not (toks and toks[0][3] == "esac"):
                for t in toks[:close]:
                    if t[0] == "word" and _sh_literal(t[3]).strip():
                        claim(t[1], t[2], "code_branch")
                self.pattern_next = False
                start = close + 1
        segments, seg = [], []
        for t in toks[start:]:
            if t[0] == "sep":
                segments.append((seg, t[3]))
                seg = []
            elif t[0] == "word":
                seg.append(t)
        segments.append((seg, None))
        array_next = False
        for words, sep in segments:
            if array_next:
                for w in words:
                    if _sh_value(w[3]):
                        claim(w[1], w[2], "code_table")
                array_next = False
                continue
            i = 0
            while i < len(words) and words[i][3] in _SH_KEYWORDS:
                if words[i][3] in {"if", "elif", "while", "until"}:
                    self.condition = True
                elif words[i][3] in {"then", "do"}:
                    self.condition = False
                i += 1
            if i < len(words) and words[i][3] == "case":
                self.case += 1
                self.pattern_next = True
                continue
            if i < len(words) and words[i][3] == "esac":
                self.case = max(0, self.case - 1)
                self.pattern_next = False
                continue
            while i < len(words):
                w = words[i][3]
                if w in _SH_DECLARE or (w.startswith("-") and i and words[i - 1][3] in _SH_DECLARE):
                    i += 1
                    continue
                m = re.match(r"[A-Za-z_]\w*(?:\[[^\]]*\])?\+?=", w)
                if not m:
                    break
                if m.end() == len(w) and sep == "(":
                    array_next = True
                elif _sh_value(w[m.end():]):
                    claim(words[i][1] + m.end(), words[i][2], "code_table")
                i += 1
            if i >= len(words):
                continue
            cmd, args = words[i][3], words[i + 1:]
            if cmd in {"[", "[["}:
                for w in args:
                    if w[3] in {"]", "]]"}:
                        break
                    if _sh_operand(w[3]):
                        claim(w[1], w[2], "code_branch")
            elif cmd == "test" or self.condition:
                for w in args:
                    if _sh_operand(w[3]):
                        claim(w[1], w[2], "code_branch")
            elif cmd == "for" and len(args) >= 2 and args[1][3] == "in":
                for w in args[2:]:
                    if _sh_value(w[3]):
                        claim(w[1], w[2], "code_table")
            for j, w in enumerate(args):
                m = re.match(r"--[\w-]+=", w[3])
                if m and _sh_value(w[3][m.end():]):
                    claim(w[1] + m.end(), w[2], "code_table")
                elif re.fullmatch(r"--[\w-]+", w[3]) and j + 1 < len(args) and \
                        not args[j + 1][3].startswith("-") and _sh_value(args[j + 1][3]):
                    claim(args[j + 1][1], args[j + 1][2], "code_table")
            if sep == ";;" and self.case:
                self.pattern_next = True
        if any(t[0] == "sep" and t[3] == ";;" for t in toks) and self.case:
            self.pattern_next = True
        return spans


def _shell_units(text: str):
    """Units of a shell script (#4091): its code spans, its comments and the
    rest of each line as `value`."""
    spans_of = _ShellSpans()
    for i, line in enumerate(text.splitlines(), 1):
        for unit, ctx in _split_units(line, spans_of(line), "value"):
            yield i, ctx, unit, line


_JS_TOKEN = re.compile(r"""'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`|//.*$|[\[\](){}]""")


def _js_spans(line: str) -> list:
    """Code spans of a JavaScript line (a github-script step, #4091): a string
    compared (`===`, `!=`, ...), a `case` label or an argument of
    `.includes`, `.startsWith`, `.endsWith`, `.indexOf` is a branch; a bare
    string assigned, used as an object value, an array item, a default
    (`||`, `??`), a conditional value or a return value is a table."""
    spans, stack = [], []
    for m in _JS_TOKEN.finditer(line):
        t = m.group(0)
        if t.startswith("//"):
            spans.append((m.start(), len(line), "comment"))
            break
        if t in "[({":
            stack.append(t)
            continue
        if t in "])}":
            if stack:
                stack.pop()
            continue
        content = t[1:-1]
        if t[0] == "`" and "${" in content:
            continue
        before, after = line[:m.start()].rstrip(), line[m.end():].lstrip()
        if (before.endswith(("===", "!==", "==", "!=")) or after.startswith(("===", "!==", "==", "!="))
                or re.search(r"(?:^|[^\w$.])case$", before)
                or re.search(r"\.(?:includes|startsWith|endsWith|indexOf|lastIndexOf)\($", before)):
            spans.append((m.start(), m.end(), "code_branch"))
        elif content and not re.search(r"\s", content) and (
                re.search(r"(?:^|[^=!<>])=$|=>$|:$|\|\|$|\?\?$|\?$|\[$|\breturn$", before)
                or (before.endswith(",") and stack and stack[-1] == "[")):
            spans.append((m.start(), m.end(), "code_table"))
    return spans


_GH_EXPR = re.compile(r"\$\{\{(.*?)\}\}")
_GH_LITERAL = re.compile(r"'(?:[^']|'')*'")
_GH_COMPARE = ("==", "!=", "<=", ">=", "<", ">")


_GH_TESTS = frozenset({"contains", "startswith", "endswith"})


def _enclosing_calls(text: str, at: int) -> list[str]:
    """The names of the calls whose parentheses enclose position `at`,
    innermost first."""
    out, depth = [], 0
    for k in range(at - 1, -1, -1):
        if text[k] == ")":
            depth += 1
        elif text[k] == "(":
            if depth == 0:
                m = re.search(r"([A-Za-z_]\w*)\s*$", text[:k])
                out.append(m.group(1).lower() if m else "")
            else:
                depth -= 1
    return out


def _expr_spans(text: str, base: int = 0) -> list:
    """Code spans of a GitHub Actions expression (an `if:` value or the inside
    of `${{ }}`, #4091): a literal compared or tested by `contains`,
    `startsWith` or `endsWith` is a branch, also as the JSON a `fromJSON`
    inside the test parses (`contains(fromJSON('["CHORUS"]'), x)`, #4130); a
    literal after `||` or `&&` (a default, a conditional value) and any other
    `fromJSON` literal (data the expression reads) is a table."""
    out = []
    for m in _GH_LITERAL.finditer(text):
        before, after = text[:m.start()].rstrip(), text[m.end():].lstrip()
        calls = _enclosing_calls(text, m.start())
        inner = calls[1:] if calls[:1] == ["fromjson"] else calls
        if before.endswith(_GH_COMPARE) or after.startswith(_GH_COMPARE) or inner[:1] and inner[0] in _GH_TESTS:
            ctx = "code_branch"
        elif before.endswith(("||", "&&")) or calls[:1] == ["fromjson"]:
            ctx = "code_table"
        else:
            continue
        out.append((base + m.start(), base + m.end(), ctx))
    return out


def _gh_expr_spans(line: str) -> list:
    out = []
    for m in _GH_EXPR.finditer(line):
        out += _expr_spans(m.group(1), m.start(1))
    return out


def _yaml_bare(item: str) -> bool:
    """A YAML scalar with no whitespace: not an anchor, alias, tag, block,
    flow collection or expression."""
    if not item or item[0] in "&*!{[|>" or "${{" in item:
        return False
    s = item[1:-1] if len(item) > 1 and item[0] == item[-1] and item[0] in "'\"" else item
    return bool(s) and not re.search(r"\s", s)


def _yaml_value_spans(body: str, at: int) -> list:
    """A bare scalar value, or each bare item of a flow sequence, from position
    `at` of a data line: a table entry (#4091)."""
    value = body[at:]
    v = value.strip()
    start = at + len(value) - len(value.lstrip())
    if v.startswith("[") and v.endswith("]"):
        out = []
        for m in re.finditer(r"""'[^']*'|"(?:[^"\\]|\\.)*"|[^,\s][^,]*""", v[1:-1]):
            item = m.group(0).rstrip()
            if _yaml_bare(item):
                out.append((start + 1 + m.start(), start + 1 + m.start() + len(item), "code_table"))
        return out
    return [(start, start + len(v), "code_table")] if _yaml_bare(v) else []


_BLOCK_SCALAR = re.compile(r"[|>][0-9+-]*")
#: A key `_KEY` does not read, such as a file path (`src/x/CHORUS.md:` in the
#: pin registry): a key for the context, never a per-project table key.
_PATH_KEY = re.compile(r"""^(\s*)(?:-\s+)?([^\s#'"{}\[\],&*!|>][^\s#]*?):(\s|$)""")


def _yaml_code_units(text: str):
    """Units of a YAML, workflow or config file that no approach hands to a
    model and some approach runs on (#4091): the contexts `_yaml_units`
    gives, with the code in it split out. A workflow's `if:` values and `${{
    }}` expressions, its `run:` blocks (shell) and `script:` blocks
    (github-script) are read as code; a key (`CM4AI:`) or a bare value
    (`project: CHORUS`, a flow or block list item) of the data is a table. A
    key that names a file path is not a key here (`_KEY` excludes `/`): the
    pin registry's paths stay values. Prose keys keep their text."""
    stack: list[tuple[int, str]] = []
    block = None                    # (indent, lang, shell state, context)
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if block is not None:
            if not stripped:
                continue
            if indent > block[0]:
                spans = _gh_expr_spans(line)
                if block[1] == "shell":
                    spans = _merge(spans, block[2](line))
                elif block[1] == "js":
                    spans = _merge(spans, _js_spans(line))
                elif block[1] == "expr":
                    spans = _merge(spans, _expr_spans(line))
                for unit, ctx in _split_units(line, spans, block[3]):
                    yield i, ctx, unit, line
                continue
            block = None
        if not stripped:
            continue
        if stripped.startswith("#"):
            yield i, "comment", line, line
            continue
        body, comment = line, ""
        hash_at = re.search(r"\s#\s", line)
        if hash_at and line.count('"', 0, hash_at.start()) % 2 == 0 and \
                line.count("'", 0, hash_at.start()) % 2 == 0:
            body, comment = line[:hash_at.start()], line[hash_at.start():]
        m = _KEY.match(body)
        path_key = None if m else _PATH_KEY.match(body)
        key_indent = 0
        if m or path_key:
            k = m or path_key
            key_indent = len(k.group(1)) + (2 if body.lstrip().startswith("- ") else 0)
            while stack and stack[-1][0] >= key_indent:
                stack.pop()
            stack.append((key_indent, k.group(2).strip("'\"").lower()))
        else:
            while stack and stack[-1][0] > indent:
                stack.pop()
        keys = [k for _, k in stack]
        meta = [not (n and keys[n - 1] in _NAME_CONTAINERS) for n in range(len(keys))]
        if any(k in _EXAMPLE_KEYS and meta[n] for n, k in enumerate(keys)):
            context = "example"
        elif keys and keys[-1] in _PROSE_KEYS and meta[-1]:
            context = "prose"
        else:
            context = "value"
        spans = _gh_expr_spans(body)
        if m:
            key = m.group(2).strip("'\"")
            lowkey = key.lower()
            if re.fullmatch(r"[\w.-]+", key):
                spans = _merge(spans, [(m.start(2), m.end(2), "code_table")])
            value = body[m.end():]
            if _BLOCK_SCALAR.fullmatch(value.strip()):
                lang = {"run": "shell", "script": "js", "if": "expr"}.get(lowkey)
                block = (key_indent, lang, _ShellSpans() if lang == "shell" else None,
                         "value" if lang else context)
            elif lowkey == "if" and value.strip():
                spans = _merge(spans, _expr_spans(value, m.end()))
            elif lowkey == "run" and value.strip():
                spans = _merge(spans, [(a + m.end(), b + m.end(), c) for a, b, c in _ShellSpans()(value)])
            elif value.strip() and context != "prose":
                spans = _merge(spans, _yaml_value_spans(body, m.end()))
        else:
            item = re.match(r"(\s*-\s+)(\S.*)$", body)
            if item and context != "prose":
                spans = _merge(spans, _yaml_value_spans(body, item.start(2)))
        for unit, ctx in _split_units(body, spans, context):
            yield i, ctx, unit, line
        if comment:
            yield i, "comment", comment, line


_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
#: One character of a JSON string as written: an escape (a surrogate pair's
#: two `\u` escapes together, as they decode to one character) or a plain
#: character (#4142).
_JSON_CHAR = re.compile(r"\\u[dD][89abAB][0-9a-fA-F]{2}\\u[dD][c-fC-F][0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}|\\.|[^\\]",
                        re.S)


def _json_decoded(body: str) -> tuple[str, list[int]]:
    """A JSON string's body (the text between its quotes, as written)
    decoded, and where each decoded character starts in `body`, with
    `len(body)` last: the decoded span `(a, b)` is `body[at[a]:at[b]]` as
    written (#4142)."""
    chars, at = [], []
    for m in _JSON_CHAR.finditer(body):
        chars.append(json.loads(f'"{m.group(0)}"'))
        at.append(m.start())
    return "".join(chars), at + [len(body)]


def _command_spans(command: str) -> list:
    """The shell spans of a command string, its lines read in order with one
    state, as the shell runs them."""
    spans_of, out, start = _ShellSpans(), [], 0
    for part in command.split("\n"):
        out += [(start + a, start + b, c) for a, b, c in spans_of(part)]
        start += len(part) + 1
    return out


def _json_code_units(text: str):
    """Units of a JSON file that no approach hands to a model and some
    approach runs on (#4130): the project settings a session applies (its
    `env` block reaches every command it runs), an allow-list the workflow
    reads. A key, or a string value with no whitespace, is a table entry
    (`"D4D_MANIFEST": "data/CHORUS_manifest.yaml"`, `"CM4AI": [...]`); a
    hook's `command` value is read as shell, as the shell gets it: its JSON
    escapes (`\\"`, `\\\\`, `\\n`) decoded, each span mapped back to the
    line as written (#4142); any other value keeps its text (`value`).
    Tokens are matched in the text as written, so one spelled with a `\\u`
    escape is not found. Read line by line, so a key and its value on
    separate lines are not paired."""
    for i, line in enumerate(text.splitlines(), 1):
        spans, key = [], None
        for m in _JSON_STRING.finditer(line):
            try:
                value = json.loads(m.group(0))
            except ValueError:
                continue
            if line[m.end():].lstrip().startswith(":"):
                key = value
                if re.fullmatch(r"[\w.-]+", value):
                    spans.append((m.start(), m.end(), "code_table"))
                continue
            if key == "command":
                decoded, at = _json_decoded(m.group(0)[1:-1])
                spans += [(m.start() + 1 + at[a], m.start() + 1 + at[b], c) for a, b, c in _command_spans(decoded)]
            elif value and not re.search(r"\s", value):
                spans.append((m.start(), m.end(), "code_table"))
        for unit, ctx in _split_units(line, spans, "value"):
            yield i, ctx, unit, line


def units_for(path: Path, rel: str, text: str, tree=None, code: bool = False):
    """The units of one file, each with its context. `code` is true for a
    YAML, config, shell or JSON file that no approach hands to a model and
    some approach runs on (#4091, #4130): its expressions, scripts and data
    tables are code."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return _python_units(text, tree)
    if suffix in {".md", ".txt"}:
        return _markdown_units(text, prompt_header=rel.startswith("src/download/prompts/")
                               and "## Prompt body" in text)
    if suffix in {".yaml", ".yml", ".config"}:
        return _yaml_code_units(text) if code else _yaml_units(text)
    if suffix == ".sh":
        return _shell_units(text)
    if suffix == ".json" and code:
        return _json_code_units(text)
    return ((i, "value", line, line) for i, line in enumerate(text.splitlines(), 1))


# --------------------------------------------------------------------------
# surfaces


@dataclass
class Surface:
    """One file and how each approach reaches it (#4054). `roles` maps an
    approach to the file's role in it; `runs` holds the approaches under
    which the file runs as a script (its `__main__` block executes: a module
    an approach only imports never runs that block); `text_spans` are line
    ranges of run-shaping code whose text reaches a model, found by data flow
    at discovery; `loaded` maps an approach to the line ranges it loads into
    the model whatever the file's role there (the description of an agent,
    command or skill that a session lists, #4091); `raw` holds the approaches
    whose model reads the file raw, comments included (a text names it for
    the model to Read, #4091)."""
    path: str
    approaches: list[str]
    role: str
    status: str
    why: str
    roles: dict = field(default_factory=dict)
    runs: set | None = None
    text_spans: list = field(default_factory=list)
    loaded: dict = field(default_factory=dict)
    raw: set = field(default_factory=set)

    def __post_init__(self):
        if not self.roles:
            self.roles = {a: self.role for a in self.approaches}
        if self.runs is None:
            self.runs = set(self.approaches)

    def as_dict(self) -> dict:
        return {"path": self.path, "approaches": list(self.approaches), "role": self.role, "status": self.status,
                "why": self.why, "roles": dict(self.roles), "runs_as_script_in": sorted(self.runs),
                "text_spans": [list(s) for s in self.text_spans],
                "loaded": {a: [list(s) for s in v] for a, v in sorted(self.loaded.items())},
                "read_raw_in": sorted(self.raw)}


class Surfaces:
    def __init__(self):
        self.files: dict[str, Surface] = {}

    def add(self, rel: str, approach: str, role: str, status: str, why: str, *, runs: bool = True,
            raw: bool = False):
        """Add one route to a file. `runs` says whether this route executes
        the file as a script (False for an import closure); `raw` whether its
        model reads the file raw (a text names it for the model to Read)."""
        cur = self.files.get(rel)
        if cur is None:
            cur = self.files[rel] = Surface(rel, [], role, status, why, roles={}, runs=set())
        if approach not in cur.approaches:
            cur.approaches.append(approach)
        old = cur.roles.get(approach)
        if old is None or ROLE_RANK[role] > ROLE_RANK[old]:
            cur.roles[approach] = role
        if runs:
            cur.runs.add(approach)
        if raw:
            cur.raw.add(approach)
        if ROLE_RANK[role] > ROLE_RANK[cur.role]:
            cur.role, cur.why = role, why
        if cur.status != "live" and status == "live":
            cur.status = status


_RESOLVED: dict[str, Path] = {}


def _resolved(p: Path) -> Path:
    """`p.resolve()`, once per path spelling per process: discovery resolves
    the same few hundred paths thousands of times."""
    key = str(p)
    r = _RESOLVED.get(key)
    if r is None:
        r = _RESOLVED[key] = p.resolve()
    return r


def _rel(root: Path, p: Path) -> str:
    return _resolved(p).relative_to(_resolved(root)).as_posix()


def _is_inside(p: Path, root: Path) -> bool:
    try:
        _resolved(p).relative_to(_resolved(root))
        return True
    except ValueError:
        return False


_PARSED: dict[str, tuple] = {}


def _parse(p: Path):
    """(text, tree) of a Python file, parsed once per process and content of
    the file (a rewrite of the same size within one mtime tick is still a
    new version); (None, None) when it cannot be read as UTF-8 or parsed,
    and `_parse_problem` says why."""
    key = str(_resolved(p))
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError, ValueError) as exc:
        _PARSED[key] = (None, None, f"{type(exc).__name__}: {exc}")
        return None, None
    entry = _PARSED.get(key)
    if entry is None or entry[0] != text:
        try:
            entry = (text, ast.parse(text), None)
        except (SyntaxError, ValueError) as exc:
            entry = (text, None, f"{type(exc).__name__}: {exc}")
        _PARSED[key] = entry
    return (entry[0], entry[1]) if entry[1] is not None else (None, None)


def _parse_problem(p: Path) -> str:
    """Why `_parse` gave nothing for a file: the read or parse error."""
    entry = _PARSED.get(str(_resolved(p)))
    return entry[2] if entry and entry[2] else "not parsed"


def _tree(path: Path) -> ast.Module:
    """The parsed module a derivation reads; one that cannot be read or parsed
    stops the scan (exit 2)."""
    _, tree = _parse(path)
    if tree is None:
        raise ConfigError(f"{path} cannot be read or parsed")
    return tree


def _module_constants(path: Path) -> dict[str, object]:
    """Module-level literals and Path expressions, evaluated without import."""
    _, tree = _parse(path)
    if tree is None:
        raise ConfigError(f"{path} cannot be read or parsed")
    env: dict[str, object] = {}

    def ev(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path" \
                and len(node.args) == 1:
            v = ev(node.args[0])
            return v if isinstance(v, str) else None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id in {"frozenset", "set", "tuple"} and len(node.args) == 1:
            v = ev(node.args[0])
            return tuple(v) if isinstance(v, (list, tuple, set)) else None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            a, b = ev(node.left), ev(node.right)
            return f"{a}/{b}" if isinstance(a, str) and isinstance(b, str) else None
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            vals = [ev(e) for e in node.elts]
            return None if any(v is None for v in vals) else tuple(vals)
        if isinstance(node, ast.Dict):
            out = {}
            for k, v in zip(node.keys, node.values):
                kk, vv = ev(k), ev(v)
                if kk is None:
                    return None
                out[kk] = vv
            return out
        return None

    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name):
                v = ev(value)
                if v is not None:
                    env[t.id] = v
    return env


def _module_role(p: Path) -> str:
    """model_facing for a module MODEL_FACING_MODULES names: a top-level
    module of the `data_sheets_schema` package, matched by its place in the
    package and not its stem alone (`cli/healthsheet.py` is not
    `healthsheet.py`)."""
    return "model_facing" if _package_module_name(p) in MODEL_FACING_MODULES else "run_shaping"


def _package_module_name(p: Path) -> str | None:
    """`name` for src/data_sheets_schema/<name>.py or <name>/__init__.py, else None."""
    if p.name == "__init__.py":
        return p.parent.name if p.parent.parent.name == "data_sheets_schema" else None
    return p.stem if p.parent.name == "data_sheets_schema" else None


def _package_module(rel: str) -> bool:
    """A module of the `data_sheets_schema` package (run with `-m`, never by
    its path)."""
    return rel.startswith("src/data_sheets_schema/")


def _package_closure(root: Path, starts: list[str], package: str = "data_sheets_schema",
                     base: str = "src") -> list[Path]:
    """Every module of `package` statically imported from the start modules."""
    def path_of(mod: str) -> Path | None:
        p = root / base / Path(*mod.split("."))
        if _exists_exact(p.with_suffix(".py")):
            return p.with_suffix(".py")
        if _exists_exact(p) and (p / "__init__.py").exists():
            return p / "__init__.py"
        return None

    seen: dict[str, Path] = {}
    todo = list(starts)
    while todo:
        mod = todo.pop()
        if mod in seen:
            continue
        p = path_of(mod)
        if p is None:
            continue
        seen[mod] = p
        _, tree = _parse(p)
        if tree is None:            # a module the closure cannot read stops the scan (#4092)
            raise _unparsed([f"{_rel(root, p)} ({_parse_problem(p)})"])
        for node in _summary(tree)["imports"]:
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    pkg = mod.split(".")[: -node.level] if p.name != "__init__.py" else \
                        mod.split(".")[: len(mod.split(".")) - node.level + 1]
                    stem = ".".join(pkg + ([node.module] if node.module else []))
                else:
                    stem = node.module or ""
                names = [stem] + [f"{stem}.{a.name}" for a in node.names]
            for n in names:
                if n == package or n.startswith(package + "."):
                    todo.append(n)
    return sorted(set(seen.values()))


_LISTINGS: dict[tuple, frozenset] = {}


def _exists_exact(p: Path) -> bool:
    """Existence with the exact spelling: on a case-insensitive filesystem
    `constants/PROJECTS.py` "exists" because `projects.py` does, and an
    imported constant named PROJECTS would be taken for a module. Listings
    are cached per directory version (its mtime moves when an entry is
    added or removed)."""
    try:
        key = (str(p.parent), p.parent.stat().st_mtime_ns)
        if key not in _LISTINGS:
            _LISTINGS[key] = frozenset(c.name for c in p.parent.iterdir())
        return p.name in _LISTINGS[key]
    except OSError:
        return False


def _module_at(base: Path, dotted: str) -> Path | None:
    """The module file `dotted` names under an import base (a directory on
    sys.path), spelled exactly; None when there is none."""
    q = base.joinpath(*dotted.split(".")) if dotted else base
    if dotted and _exists_exact(q.with_suffix(".py")) and q.with_suffix(".py").is_file():
        return _resolved(q.with_suffix(".py"))
    if (not dotted or _exists_exact(q)) and _exists_exact(q / "__init__.py"):
        return _resolved(q / "__init__.py")
    return None


def _schema_closure(schema_dir: Path, root_name: str) -> list[Path]:
    seen, todo = [], [schema_dir / root_name]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        if not p.exists():
            raise ConfigError(f"schema module not found: {p}")
        seen.append(p)
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for name in doc.get("imports") or []:
            if not name.startswith("linkml:"):
                todo.append(p.parent / f"{name}.yaml")
    return seen


# --------------------------------------------------------------------------
# the runner's conditions, derived from the code (#4025: never a fallback)


def derive_cli_default(tree: ast.Module, prompts: dict) -> str:
    """The condition `d4d api` uses when no --condition is given: the value
    assigned to `condition` inside `if condition is None:`. Either spelling
    (`condition = "x"` or `condition, kw[...] = "x", False`) is read; none,
    two different ones, or one that is not a registered condition is not
    derived, never the constant "generic"."""
    found = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "condition"
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Is)
                and isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value is None):
            continue
        for stmt in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "condition":
                    value = stmt.value
                elif isinstance(target, ast.Tuple) and isinstance(stmt.value, ast.Tuple):
                    pos = [i for i, t in enumerate(target.elts) if isinstance(t, ast.Name) and t.id == "condition"]
                    value = stmt.value.elts[pos[0]] if pos and pos[0] < len(stmt.value.elts) else None
                else:
                    continue
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    found.add(value.value)
    if len(found) != 1:
        raise _not_derived("the CLI default condition",
                           f"cli/api.py assigns {sorted(found) or 'nothing'} to `condition` under "
                           "`if condition is None:`")
    default = found.pop()
    if default not in prompts:
        raise _not_derived("the CLI default condition", f"{default!r} is not in api_runner.CONDITION_PROMPTS")
    return default


def _required(env: dict, name: str, kind: type, *, nonempty: bool = False):
    value = env.get(name)
    if not isinstance(value, kind) or (nonempty and not value):
        raise _not_derived(f"api_runner.{name}", f"not a module-level {kind.__name__} literal"
                           + (" with at least one entry" if nonempty else ""))
    return value


def _render_joined(node: ast.JoinedStr, upper: bool = True) -> str:
    """An f-string with each placeholder named after its last attribute:
    f"{spec.project}.md" -> "{PROJECT}.md" (or "{project}.md")."""
    out = []
    for v in node.values:
        if isinstance(v, ast.Constant):
            out.append(str(v.value))
        elif isinstance(v, ast.FormattedValue):
            name = _attr_or_name(v.value) or "..."
            out.append("{" + (name.upper() if upper else name) + "}")
    return "".join(out)


def _path_text(node, local: dict, env: dict, seen=frozenset()) -> tuple[set[str], str | None]:
    """(module path constants an expression is built from, the path it spells)."""
    if isinstance(node, ast.Name):
        if node.id in local and node.id not in seen:
            return _path_text(local[node.id], local, env, seen | {node.id})
        if isinstance(env.get(node.id), str):
            return {node.id}, env[node.id]
        return set(), None
    if isinstance(node, ast.Call) and node.args:          # resource_path(X), Path(X)
        return _path_text(node.args[0], local, env, seen)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        a, ta = _path_text(node.left, local, env, seen)
        b, tb = _path_text(node.right, local, env, seen)
        return a | b, (f"{ta}/{tb}" if ta is not None and tb is not None else None)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return set(), node.value
    if isinstance(node, ast.JoinedStr):
        return set(), _render_joined(node)
    return set(), None


def derive_tuned_reads(tree: ast.Module, env: dict) -> dict:
    """What `resolve_prompt` puts into a `tuned` instruction (#4058): the
    path constants whose file text it reads inside its `if spec.condition ==
    "tuned":` block, as against the ones it only names (in a header line).
    Not found is not derived."""
    fn = _function(tree, "resolve_prompt")
    if fn is None:
        raise _not_derived("the tuned condition's text", "api_runner.py defines no resolve_prompt")
    blocks = [n for n in ast.walk(fn) if isinstance(n, ast.If) and any(
        isinstance(op, ast.Eq) and {_attr_or_name(lt), _attr_or_name(rt)} & {"condition"}
        and "tuned" in {getattr(lt, "value", None), getattr(rt, "value", None)}
        for lt, op, rt in _compares(n.test))]
    if not blocks:
        raise _not_derived("the tuned condition's text", "resolve_prompt has no `condition == \"tuned\"` block")
    paths = {k for k, v in env.items() if isinstance(v, str) and "/" in v}
    reads, read_paths, named = set(), set(), set()
    for block in blocks:
        local = {t.id: n.value for n in ast.walk(block) if isinstance(n, ast.Assign)
                 for t in n.targets if isinstance(t, ast.Name)}
        for n in ast.walk(block):
            if isinstance(n, ast.Name) and n.id in paths:
                named.add(n.id)
            if not isinstance(n, ast.Call):
                continue
            callee = _attr_or_name(n.func)
            if isinstance(n.func, ast.Attribute) and callee in {"read_text", "read_bytes"}:
                target = n.func.value
            elif callee in {"open", "prompt_body"} and n.args:
                target = n.args[0]
            else:
                continue
            consts, text = _path_text(target, local, env)
            reads |= consts & paths
            if text is not None and consts & paths:
                read_paths.add(text)
    return {"reads": sorted(reads), "named_only": sorted(named - reads), "appends": sorted(read_paths),
            "line": blocks[0].lineno}


def condition_table(root: Path) -> dict:
    """The runner's conditions, read from api_runner.py and cli/api.py by ast."""
    env = _module_constants(root / RUNNER)
    prompts = _required(env, "CONDITION_PROMPTS", dict, nonempty=True)
    if not all(isinstance(v, str) for v in prompts.values()):
        raise _not_derived("api_runner.CONDITION_PROMPTS", "a prompt path is not a literal")
    versions = {c: int(m.group(1)) for c in prompts if (m := re.fullmatch(r"generic_v(\d+)", c))}
    if not versions:
        raise _not_derived("the current generic condition", "no generic_vN in CONDITION_PROMPTS")
    current = max(versions, key=versions.get)
    default = derive_cli_default(_tree(root / CLI_API), prompts)
    live = sorted({current, default})
    tuned = "tuned" in prompts
    reads = None
    if tuned:
        reads = derive_tuned_reads(_tree(root / RUNNER), env)
        reads["sends_tuned_prompt"] = "TUNED_PROMPT" in reads["reads"]
        reads["sends_components"] = "COMPONENTS" in reads["reads"]
    return {"prompts": prompts, "current": current, "default": default, "live": live,
            "tuned_prompt": _required(env, "TUNED_PROMPT", str) if tuned else None,
            "components": _required(env, "COMPONENTS", str) if tuned else None,
            "tuned": reads,
            "receipt_conditions": sorted(_required(env, "RECEIPT_CONDITIONS", tuple)),
            "phases": list(_required(env, "PHASES", tuple, nonempty=True)),
            "derived_phases": sorted(_required(env, "DERIVED_PHASES", tuple)),
            "core_derived": _required(env, "CORE_DERIVED", bool),
            "agentic_runtimes": sorted(_required(env, "AGENTIC_RUNTIMES", tuple, nonempty=True))}


#: Every `--condition` a command passes, with the value that follows it.
CONDITION_ARG = re.compile(r"(?<![\w-])--condition(?![\w-])(?:=|\s+)?(\S*)")


def github_assistant_run(root: Path, cond: dict) -> dict:
    """What the GitHub assistant workflow runs: its `d4d api run` command and
    the condition it names, or the CLI default when it passes no
    `--condition` at all (#4057). No workflow file is an empty result; a
    workflow with no `d4d api run`, one naming an unregistered condition, and
    one whose `--condition` is not a literal condition name (an expression,
    a variable: chosen when the workflow runs) are not derived (#4092): the
    CLI default is reported only where no `--condition` is passed."""
    yml = root / ".github/workflows/d4d-agent.yml"
    if not yml.exists():
        return {}
    text = yml.read_text(encoding="utf-8")
    m = re.search(r"d4d api run(?:[^\n]*\\\n)*[^\n]*", text)
    if m is None:
        raise _not_derived("what the GitHub assistant runs", "d4d-agent.yml has no `d4d api run` command")
    block = m.group(0)
    values = []
    for cm in CONDITION_ARG.finditer(block.replace("\\\n", " ")):
        lit = re.fullmatch(r"(['\"]?)([A-Za-z_][\w.-]*)\1", cm.group(1))
        if lit is None:
            raise _not_derived("what the GitHub assistant runs",
                               f"its `d4d api run` passes `--condition {cm.group(1)}`, which is not a literal "
                               "condition name: the condition is chosen when the workflow runs, and reporting the "
                               "CLI default would be false")
        values.append(lit.group(2))
    if len(set(values)) > 1:
        raise _not_derived("what the GitHub assistant runs",
                           f"its `d4d api run` passes --condition {sorted(set(values))}")
    name = values[0] if values else cond["default"]
    if name not in cond["prompts"]:
        raise _not_derived("what the GitHub assistant runs", f"--condition {name} is not a registered condition")
    return {"command": " ".join(block.replace("\\\n", " ").split()), "condition_name": name,
            "condition_basis": "--condition" if values else "CLI default (no --condition)",
            "condition": name if values else f"{name} (CLI default; no --condition)",
            "manifest": "given" if "--manifest" in block else "none passed (neutral for an external bundle)"}


# --------------------------------------------------------------------------
# discovery from the code (#4023, #4054)


def _is_test(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    return (any(part in {"tests", "test"} for part in parts[:-1]) or name.startswith("test_")
            or name.endswith("_test.py") or name == "conftest.py")


def _walk_sources(root: Path, tops=PYTHON_ROOTS) -> tuple[list[Path], int, list[str]]:
    """One walk of the trees code runs from: every non-test Python file minus
    registered byte copies (frozen run evidence) and hidden directories, how
    many registered copies were skipped, and the nested CLAUDE.md files
    Claude Code would load in a session that reads that subtree."""
    out, skipped, memory = [], 0, []
    for top in tops:
        base = root / top
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for name in sorted(filenames):
                p = Path(dirpath) / name
                rel = _rel(root, p)
                if name == "CLAUDE.md" and not REGISTERED_COPY.search(rel):
                    memory.append(rel)
                if not name.endswith(".py") or _is_test(rel):
                    continue
                if REGISTERED_COPY.search(rel):
                    skipped += 1
                    continue
                out.append(_resolved(p))    # resolved: import resolution compares resolved paths
    return sorted(out), skipped, sorted(memory)


def _python_sources(root: Path, tops=PYTHON_ROOTS) -> tuple[list[Path], int]:
    """Every non-test Python file under the trees code runs from, minus
    registered byte copies and hidden directories, and how many registered
    copies were skipped."""
    out, skipped, _ = _walk_sources(root, tops)
    return out, skipped


def _dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return f"{_dotted(node.func)}()"
    return "?"


_SUMMARIES: dict[int, tuple] = {}


def _summary(tree) -> dict:
    """What discovery reads from a module, in one walk of its tree: its
    imports, its calls (dotted callee, line), the generation builders it
    uses as code and its string constants. Cached per tree; the entry holds
    the tree, so its id cannot be reused while cached."""
    entry = _SUMMARIES.get(id(tree))
    if entry is not None and entry[0] is tree:
        return entry[1]
    imports, calls, builders, strings = [], [], set(), []
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            imports.append(n)
        elif isinstance(n, ast.Call):
            calls.append((_dotted(n.func), n.lineno))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            strings.append(n.value)
        if isinstance(n, ast.Name) and n.id in GENERATION_BUILDERS:
            builders.add(n.id)
        elif isinstance(n, ast.Attribute) and n.attr in GENERATION_BUILDERS:
            builders.add(n.attr)
        elif isinstance(n, ast.alias) and n.name.split(".")[-1] in GENERATION_BUILDERS:
            builders.add(n.name.split(".")[-1])
    summary = {"imports": imports, "calls": calls, "builders": sorted(builders), "strings": strings}
    _SUMMARIES[id(tree)] = (tree, summary)
    return summary


def model_call_sites(tree) -> list[tuple[str, int]]:
    """Calls that send a request to a model, read from the code (a comment or
    docstring that mentions one is not a call)."""
    return [(name, line) for name, line in _summary(tree)["calls"]
            if MODEL_CALL.search(name) or AGENT_RUN.search(name)]


def model_client_evidence(tree) -> list[str]:
    """Why a module is a model client: a client package import or a call site."""
    why = set()
    for node in _summary(tree)["imports"]:
        if isinstance(node, ast.Import):
            why.update(f"import {a.name}" for a in node.names if a.name.split(".")[0] in MODEL_CLIENT_PACKAGES)
        elif not node.level and (node.module or "").split(".")[0] in MODEL_CLIENT_PACKAGES:
            why.add(f"from {node.module} import")
    why.update(f"{name}()" for name, _ in model_call_sites(tree))
    return sorted(why)


def _builders_used(tree) -> list[str]:
    return _summary(tree)["builders"]


def _str_constants(tree) -> list[str]:
    return _summary(tree)["strings"]


def _notes_index(root: Path, parsed: dict) -> dict[str, list[Path]]:
    """notes/ module and package names -> their files, for imports a
    controller resolves through another experiment directory on sys.path."""
    index: dict[str, list[Path]] = {}
    for p in parsed:
        if not _rel(root, p).startswith("notes/"):
            continue
        name = p.parent.name if p.name == "__init__.py" else p.stem
        index.setdefault(name, []).append(p)
    return index


def _resolve_module(root: Path, p: Path, dotted: str, level: int, index: dict) -> Path | None:
    """The file an import in module `p` resolves to: a relative import from
    its package; `data_sheets_schema.*` from src/; `src.*` from the checkout
    root (setup_repo_imports puts it on sys.path); otherwise through the
    module's own directory or an ancestor below notes/ (the controllers put
    the experiment directory on sys.path; a script run by path imports its
    siblings), and failing that the one notes/ module of that name when
    exactly one exists."""
    here = _resolved(p).parent
    if level:
        base = here
        for _ in range(level - 1):
            base = base.parent
        return _module_at(base, dotted)
    head = dotted.split(".")[0]
    if head == "data_sheets_schema":
        return _module_at(_resolved(root / "src"), dotted)
    if head == "src":
        return _module_at(_resolved(root), dotted)
    notes = _resolved(root / "notes")
    for d in [here, *[d for d in here.parents if d == notes or notes in d.parents]]:
        hit = _module_at(d, dotted)
        if hit:
            return hit
    cands = index.get(head, [])
    if len(cands) == 1:
        only = cands[0]
        return _module_at(only.parent.parent if only.name == "__init__.py" else only.parent, dotted)
    return None


_TARGETS: dict[tuple, tuple] = {}


def _local_import_targets(root: Path, p: Path, tree, index: dict[str, list[Path]]) -> list[Path]:
    """Modules under notes/ or scripts/ a module imports (relative imports, a
    sibling or an experiment directory on sys.path, the one notes/ module of
    that name). `data_sheets_schema` and `src` modules are the closures'
    business, not the controller set's. Memoized per (module, tree, index):
    the driver search asks for every module on every pass."""
    key = (str(root), str(p))
    entry = _TARGETS.get(key)
    if entry is not None and entry[0] is tree and entry[1] is index:
        return entry[2]
    targets = _resolve_local_imports(root, p, tree, index)
    _TARGETS[key] = (tree, index, targets)
    return targets


def _resolve_local_imports(root: Path, p: Path, tree, index: dict[str, list[Path]]) -> list[Path]:
    found: list[Path] = []
    for node in _summary(tree)["imports"]:
        if isinstance(node, ast.ImportFrom) and node.level:
            mod = node.module or ""
            names = [mod] + [f"{mod}.{a.name}".strip(".") for a in node.names]
            found += [t for name in names if (t := _resolve_module(root, p, name, node.level, index))]
        else:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                if not name or name.split(".")[0] in {"data_sheets_schema", "src"}:
                    continue
                t = _resolve_module(root, p, name, 0, index)
                if t is not None:
                    found.append(t)
    keep = []
    for f in found:
        if f != _resolved(p) and _is_inside(f, root) and _rel(root, f).split("/")[0] in {"notes", "scripts"}:
            keep.append(f)
    return keep


_BINDINGS: dict[tuple, tuple] = {}


def _bindings(root: Path, p: Path, tree, index: dict) -> dict[str, tuple]:
    """What each imported name in a module refers to: (module file, None) for
    a module, (module file, attribute) for a name taken from one. An import
    anywhere in the module counts: a function-level import binds the same
    name for the data flow (#4054)."""
    key = (str(root), str(p))
    entry = _BINDINGS.get(key)
    if entry is not None and entry[0] is tree and entry[1] is index:
        return entry[2]
    out: dict[str, tuple] = {}
    for node in _summary(tree)["imports"]:
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    out[a.asname] = (_resolve_module(root, p, a.name, 0, index), None)
                else:
                    head = a.name.split(".")[0]
                    out.setdefault(head, (_resolve_module(root, p, head, 0, index), None))
            continue
        mod = node.module or ""
        base = _resolve_module(root, p, mod, node.level, index) if (mod or node.level) else None
        for a in node.names:
            if a.name == "*":
                continue
            sub = _resolve_module(root, p, f"{mod}.{a.name}" if mod else a.name, node.level, index)
            out[a.asname or a.name] = (sub, None) if sub else (base, a.name)
    _BINDINGS[key] = (tree, index, out)
    return out


def _named_claude_files(text: str, names: dict[str, str]) -> set[str]:
    """`.claude/commands|agents/X.md` paths, bare names (`d4d-validator`) and
    slash commands (`/d4d-full-core`) a text uses. A bare name counts only as
    a whole hyphenated word outside a path, so `d4d-rubric10` is not found
    inside `d4d-rubric10-semantic`."""
    found = set(CLAUDE_REF.findall(text))
    for stem, rel in names.items():
        if re.search(rf"(?<![\w/.-])/?{re.escape(stem)}(?![\w-])", text):
            found.add(rel)
    return found


def _named_files(root: Path, text: str, claude_names: dict[str, str]) -> dict[str, bool]:
    """The repository files a text names, each with whether the text runs it
    (`python path.py`, `bash path.sh`, `python -m dotted.module`) (#4054): a
    playbook or agent by path, bare name or slash command; any file under
    .claude/, .github/, src/, scripts/ or notes/ by path; and the project
    memory (CLAUDE.md). Tests and the record corpus (data/) are not
    surfaces, and a templated path names no single file."""
    found: dict[str, bool] = {rel: False for rel in _named_claude_files(text, claude_names)}
    src_base, root_base = _resolved(root / "src"), _resolved(root)
    for line in text.splitlines():
        for m in NAMED_PATH.finditer(line):
            rel = m.group(1)
            if _is_test(rel) or not (root / rel).is_file():
                continue
            found[rel] = found.get(rel, False) or bool(RUN_PREFIX.search(line[:m.start()]))
        for m in MEMORY_NAME.finditer(line):
            if (root / m.group(1)).is_file():
                found.setdefault(m.group(1), False)
        for m in MODULE_RUN.finditer(line):
            p = _module_at(src_base, m.group(1)) or _module_at(root_base, m.group(1))
            if p is not None and _is_inside(p, root) and not _is_test(_rel(root, p)):
                found[_rel(root, p)] = True
    return found


def _launch_sites(root: Path, p: Path, tree, index: dict, node=None) -> list[tuple[int, str]]:
    """(line, what) for each place module `p` (or the part of it at `node`)
    starts a generation run (#4054): it calls the runner's `execute`, or
    hands a native runtime a system prompt or a system-prompt file (#4131)."""
    runner = _resolved(root / RUNNER)
    binds = _bindings(root, p, tree, index)
    out = []
    for n in ast.walk(tree if node is None else node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and binds.get(f.id) in {(runner, "execute"), (runner, "_execute")}:
                out.append((n.lineno, f"{f.id}()"))
            elif (isinstance(f, ast.Attribute) and f.attr in {"execute", "_execute"} and isinstance(f.value, ast.Name)
                  and binds.get(f.value.id) == (runner, None)):
                out.append((n.lineno, f"{f.value.id}.{f.attr}()"))
        elif isinstance(n, ast.Constant) and _launch_flag(n):
            out.append((n.lineno, _launch_flag(n)))
    return sorted(out)


def _launch_evidence(root: Path, p: Path, tree, index: dict) -> list[str]:
    """How a module outside notes/ starts a generation run: what
    `_launch_sites` finds. A module that uses a builder only to validate,
    review or evaluate is not a launcher."""
    return sorted({what for _, what in _launch_sites(root, p, tree, index)})


def _candidate_controller(root: Path, p: Path, exclude: frozenset = frozenset()) -> str | None:
    """The tree (notes, scripts or src) of a module that may seed or run a
    generation controller, or None: a module in a generation closure, a
    diagnostic probe and an evaluator are not candidates (#4023, #4054)."""
    rel = _rel(root, p)
    top = rel.split("/")[0]
    if top not in {"notes", "scripts", "src"} or rel in exclude or "probe" in p.stem \
            or EVALUATION_PATH.search(rel):
        return None
    return top


def run_controllers(root: Path, parsed: dict, index: dict,
                    exclude: frozenset = frozenset()) -> tuple[dict[str, Path], dict[str, str], set[Path]]:
    """Generation controllers and launchers, derived from what they do rather
    than a glob list (#4023, #4054). A seed under notes/ builds or renders a
    generation request (uses RunSpec, build_phase, prompt_body, ...); a seed
    under scripts/ or src/ (outside the generation closures in `exclude`)
    builds one and launches it (calls the runner's execute, or passes a
    native runtime a system prompt). The controller set is the seeds, every
    notes/ or scripts/ module they import, and every module that runs one
    (imports one, or stages one by file name), to a fixed point. The import
    closure stops at an evaluation module (a shared sequence ledger imports
    one for evaluation sequences): those are returned apart and never gate."""
    why: dict[str, str] = {}
    for p, (_, tree) in parsed.items():
        top = _candidate_controller(root, p, exclude)
        used = _builders_used(tree) if top else []
        if not used:
            continue
        if top == "notes":
            why[_rel(root, p)] = "builds a generation request (" + ", ".join(used) + ")"
        else:
            launch = _launch_evidence(root, p, tree, index)
            if launch:
                why[_rel(root, p)] = ("launches a generation run (" + ", ".join(launch) + "; builds with "
                                      + ", ".join(used) + ")")
    controllers: dict[str, Path] = {}
    evaluation_reached: set[Path] = set()

    def close(todo: list[Path]):
        while todo:
            p = todo.pop()
            rel = _rel(root, p)
            if rel in controllers or p not in parsed:
                continue
            if EVALUATION_PATH.search(rel):
                evaluation_reached.add(p)
                continue
            controllers[rel] = p
            why.setdefault(rel, "imported or staged by a controller")
            tree = parsed[p][1]
            todo += _local_import_targets(root, p, tree, index)
            # a module the controller stages or pins by file name beside it
            # (prepare_direct.py pins bind_direct_launch.py)
            todo += [_resolved(p.parent / lit) for lit in _str_constants(tree)
                     if re.fullmatch(r"[\w.-]+\.py", lit) and _resolved(p.parent / lit) in parsed]

    close([p for p in parsed if _rel(root, p) in why])
    while True:
        names = {(p.parent, p.name) for p in controllers.values()}
        resolved = {_resolved(p): rel for rel, p in controllers.items()}
        drivers = []
        for p, (_, tree) in sorted(parsed.items()):
            rel = _rel(root, p)
            if rel in controllers or not _candidate_controller(root, p, exclude):
                continue
            imported = sorted({resolved[_resolved(t)] for t in _local_import_targets(root, p, tree, index)
                               if _resolved(t) in resolved})
            staged = sorted({lit for lit in _str_constants(tree) if (p.parent, lit) in names})
            if imported:
                why[rel] = "runs a controller (imports " + ", ".join(Path(r).name for r in imported[:3]) + ")"
            elif staged:
                why[rel] = "stages controller files by name (" + ", ".join(staged[:3]) + ")"
            else:
                continue
            drivers.append(p)
        if not drivers:
            break
        close(drivers)
    return controllers, {rel: why[rel] for rel in sorted(controllers)}, evaluation_reached


def evaluation_controllers(root: Path, parsed: dict, index: dict, controllers: dict,
                           reached: set[Path]) -> dict[str, str]:
    """Evaluation modules under notes/ that a run controller imports, or that
    drive a model through a run controller (its transport or ledger), and the
    notes/ modules they import: listed under other_model_client, never gating
    (evaluation is not generation)."""
    resolved = {_resolved(p) for p in controllers.values()}
    out: dict[str, str] = {}
    todo = []
    for p in sorted(reached):
        out[_rel(root, p)] = "evaluation module a run controller imports (an evaluation-sequence branch)"
        todo.append(p)
    for p, (_, tree) in sorted(parsed.items()):
        rel = _rel(root, p)
        if rel.startswith("notes/") and EVALUATION_PATH.search(rel) and rel not in controllers and \
                rel not in out and any(_resolved(t) in resolved for t in _local_import_targets(root, p, tree, index)):
            out[rel] = "evaluation controller: imports a run controller"
            todo.append(p)
    while todo:
        p = todo.pop()
        for t in _local_import_targets(root, p, parsed[p][1], index):
            rel = _rel(root, t)
            if t in parsed and rel not in controllers and rel not in out:
                out[rel] = "imported by an evaluation controller"
                todo.append(t)
    return dict(sorted(out.items()))


def _md_literals(tree) -> list[str]:
    return sorted({v for v in _str_constants(tree) if re.fullmatch(r"[\w.-]+\.md", v) and v.lower() != "readme.md"})


def derive_toolchain(root: Path) -> dict:
    """What `agentic_runtime.toolchain()` hands a native run, read with ast
    (#4054): `SCHEMAS`, and the directories it lists through
    `resource_names`, with the glob `resource_names` uses. Not found is not
    derived."""
    path = root / AGENTIC_RUNTIME
    tree = _tree(path)
    schemas = _module_constants(path).get("SCHEMAS")
    if not isinstance(schemas, tuple) or not schemas or not all(isinstance(s, str) for s in schemas):
        raise _not_derived("the native toolchain", "agentic_runtime.SCHEMAS is not a module-level tuple of paths")
    names, tool = _function(tree, "resource_names"), _function(tree, "toolchain")
    if names is None or tool is None:
        raise _not_derived("the native toolchain", "agentic_runtime defines no resource_names() or toolchain()")
    globs = [(_attr_or_name(n.func), a.value) for n in ast.walk(names) if isinstance(n, ast.Call)
             and _attr_or_name(n.func) in {"glob", "rglob"} for a in n.args
             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    dirs = sorted({e.value for n in ast.walk(tool) if isinstance(n, ast.For) and isinstance(n.iter, (ast.Tuple, ast.List))
                   for e in n.iter.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)})
    if len(globs) != 1 or not dirs:
        raise _not_derived("the native toolchain", f"resource_names globs {globs or 'nothing'}; toolchain() lists "
                           f"{dirs or 'no'} directories")
    return {"schemas": list(schemas), "directories": dirs, "pattern": globs[0][1],
            "recursive": globs[0][0] == "rglob"}


def derive_default_arm(tree: ast.Module) -> str:
    """The arm `d4d api` runs when given none: the `--arm` option's default."""
    found = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _attr_or_name(n.func) == "option" and \
                any(isinstance(a, ast.Constant) and a.value == "--arm" for a in n.args):
            found.update(k.value.value for k in n.keywords if k.arg == "default" and isinstance(k.value, ast.Constant))
    if len(found) != 1:
        raise _not_derived("the baseline arm", f"cli/api.py's --arm defaults are {sorted(found) or 'absent'}")
    return found.pop()


def deterministic_arm_commands(root: Path, exclude: frozenset = frozenset()) -> dict[str, str]:
    """The CLI groups that build a non-baseline arm's bundle (#4054): every
    `src/data_sheets_schema/cli/*.py` whose string literals name the bundle
    of an arm in `cli/api.py` ARMS other than the default one, except
    cli/api.py (which declares the arms) and a group already in a generation
    closure (`exclude`: `d4d download`, which the native playbook runs,
    names those bundles only to check them). Not found is not derived."""
    cli_tree = _tree(root / CLI_API)
    arms = _module_constants(root / CLI_API).get("ARMS")
    if not isinstance(arms, dict) or not arms:
        raise _not_derived("the deterministic arms", "cli/api.py ARMS is not a module-level dict literal")
    baseline = derive_default_arm(cli_tree)
    suffixes: dict[str, str] = {}
    for arm, row in arms.items():
        if arm == baseline:
            continue
        bundle = row[2] if isinstance(row, tuple) and len(row) > 2 else None
        if not isinstance(bundle, str) or "{p}" not in bundle:
            raise _not_derived("the deterministic arms", f"ARMS[{arm!r}] has no `{{p}}...` bundle pattern")
        suffixes[bundle.split("{p}", 1)[1]] = arm
    out = {}
    for p in sorted((root / "src/data_sheets_schema/cli").glob("*.py")):
        if _resolved(p) == _resolved(root / CLI_API) or _rel(root, p) in exclude:
            continue
        _, tree = _parse(p)
        if tree is None:            # a group that does not parse could be an arm command (#4092)
            raise _unparsed([f"{_rel(root, p)} ({_parse_problem(p)})"])
        lits = _str_constants(tree)
        arms_named = sorted({arm for sfx, arm in suffixes.items() if any(sfx in lit for lit in lits)})
        if arms_named:
            out[_rel(root, p)] = "names the bundle of the " + ", ".join(arms_named) + " arm" + \
                ("s" if len(arms_named) > 1 else "")
    if not out:
        raise _not_derived("the deterministic arm commands",
                           "no CLI group names a non-baseline arm bundle (" + ", ".join(sorted(suffixes)) + ")")
    return out


def _sys_path_dirs(root: Path, tree) -> list[str]:
    """Checkout directories a module puts on sys.path (`sys.path.insert(0,
    str(repo_root / ".claude" / "agents" / "scripts"))`, `.append`,
    `.extend`, `sys.path[:0] = [...]`), read from the string parts of the
    path expression; a path with no string part is the checkout root, which
    every closure already searches."""
    out = set()
    scopes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))] + [tree]
    for scope in scopes:
        nodes = list(ast.walk(scope)) if scope is not tree else list(tree.body)
        assigns = {t.id: n.value for n in nodes if isinstance(n, ast.Assign) for t in n.targets
                   if isinstance(t, ast.Name)}
        for n in (ast.walk(scope) if scope is not tree else ()):
            args = []
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and _dotted(n.func.value) == "sys.path":
                if n.func.attr == "insert" and len(n.args) == 2:
                    args = [n.args[1]]
                elif n.func.attr == "append" and n.args:
                    args = [n.args[0]]
                elif n.func.attr == "extend" and n.args and isinstance(n.args[0], (ast.List, ast.Tuple)):
                    args = list(n.args[0].elts)
            elif isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.Tuple)) and any(
                    isinstance(t, ast.Subscript) and _dotted(t.value) == "sys.path" for t in n.targets):
                args = list(n.value.elts)
            for a in args:
                parts = _string_parts(a, assigns)
                if parts and (root / Path(*parts)).is_dir():
                    out.add("/".join(parts))
    return sorted(out)


def _string_parts(node, assigns: dict, depth: int = 0) -> list[str]:
    if depth > 6:
        return []
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str" and node.args:
        return _string_parts(node.args[0], assigns, depth + 1)
    if isinstance(node, ast.Name):
        return _string_parts(assigns[node.id], assigns, depth + 1) if node.id in assigns else []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _string_parts(node.left, assigns, depth + 1) + _string_parts(node.right, assigns, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [part for part in node.value.split("/") if part]
    return []


def _import_targets(root: Path, p: Path, tree, dirs: list[str]) -> list[Path]:
    """The modules an import closure follows from one module: relative
    imports, `data_sheets_schema.*` (src/), `src.*` (the checkout root) and
    top-level names through the checkout directories the closure's code puts
    on sys.path."""
    out = []
    for node in _summary(tree)["imports"]:
        if isinstance(node, ast.ImportFrom) and node.level:
            base = _resolved(p).parent
            for _ in range(node.level - 1):
                base = base.parent
            mod = node.module or ""
            out += [t for name in [mod] + [f"{mod}.{a.name}".strip(".") for a in node.names]
                    if (t := _module_at(base, name))]
            continue
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
            [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]
        for name in names:
            if not name:
                continue
            head = name.split(".")[0]
            bases = [root / "src"] if head == "data_sheets_schema" else [root] if head == "src" else \
                [root / d for d in dirs]
            for b in bases:
                t = _module_at(_resolved(b), name)
                if t is not None:
                    out.append(t)
                    break
    return out


def _code_closure(root: Path, starts: list[Path], stop: set[Path], dirs: list[str] | None = None,
                  opaque: frozenset = frozenset()) -> tuple[list[Path], list[str]]:
    """Every module the start modules import, statically (`_import_targets`),
    with the sys.path directories the closure's own code adds found to a
    fixed point, beyond `dirs` (a script run by path has its own directory
    on sys.path). A module in `stop` (an upstream input step) is not
    entered; a module in `opaque` (the CLI package, which imports every
    group) is reached but its imports are not followed. A module the closure
    cannot read or parse stops the scan (#4092)."""
    dirs = list(dirs or [])
    added: dict[Path, list[str]] = {}
    while True:
        seen: dict[Path, ast.AST] = {}
        todo = [_resolved(p) for p in starts]
        while todo:
            p = todo.pop()
            if p in seen or p in stop:
                continue
            text, tree = _parse(p)
            if tree is None:
                raise _unparsed([f"{_rel(root, p)} ({_parse_problem(p)})"])
            seen[p] = tree
            if p in opaque:
                continue
            if p not in added:          # only a module that names sys.path can extend it
                added[p] = _sys_path_dirs(root, tree) if "sys.path" in text else []
            todo += _import_targets(root, p, tree, dirs)
        found = sorted({d for p in seen for d in added.get(p, ())} - set(dirs))
        if not found:
            return sorted(seen), dirs
        dirs += found


def shared_input_modules(root: Path) -> dict[str, str]:
    """The upstream input steps (#4054): the `src.download` modules the `d4d
    download` group imports (setup_repo_imports puts the checkout root on
    sys.path), and the src/download modules they import."""
    group = root / DOWNLOAD_GROUP
    if not group.is_file():
        return {}
    _, tree = _parse(group)
    if tree is None:
        raise ConfigError(f"{DOWNLOAD_GROUP} cannot be parsed")
    download = _resolved(root / "src/download")
    out: dict[str, str] = {}
    todo = [(t, "imported by the `d4d download` group") for t in _import_targets(root, group, tree, [])
            if t.parent == download]
    while todo:
        p, why = todo.pop()
        rel = _rel(root, p)
        if rel in out:
            continue
        out[rel] = why
        _, t = _parse(p)
        if t is not None:
            todo += [(q, "imported by an upstream input step") for q in _import_targets(root, p, t, ["src/download"])
                     if q.parent == download]
    return dict(sorted(out.items()))


def _hook_scripts(root: Path, settings: Path) -> list[str]:
    """The repository scripts a Claude Code settings file runs as hooks."""
    try:
        doc = json.loads(settings.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ConfigError(f"{settings} is not readable JSON, so its hooks cannot be followed: {exc}") from exc
    out = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "command" and isinstance(v, str):
                    for m in re.finditer(r"((?:\.claude|scripts|src|notes)/[\w./-]+)", v):
                        if (root / m.group(1)).is_file():
                            out.add(m.group(1))
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc.get("hooks") if isinstance(doc, dict) else None)
    return sorted(out)


def _cli_groups(root: Path, text: str) -> list[str]:
    """The `d4d` CLI groups a text runs (`d4d <group> <command>`, `python -m
    data_sheets_schema.cli <group> <command>`) that exist as group modules
    (#4091)."""
    out = set()
    for g in CLI_GROUP_RUN.findall(text):
        if (root / "src/data_sheets_schema/cli" / f"{g.replace('-', '_')}.py").is_file():
            out.add(g.replace("-", "_"))
    return sorted(out)


def _run_module_target(root: Path, here: Path, dotted: str) -> Path | None:
    """The file `python -m dotted` runs, from a text or code in directory
    `here`: resolved under src/, the checkout root, and `here` and its
    parents below the top-level tree (a controller is run from its experiment
    directory, `python -m audit_controls.native`). `-m package` runs the
    package's `__main__.py`."""
    if not re.fullmatch(r"[A-Za-z_]\w*(?:\.\w+)*", dotted):
        return None
    bases = [_resolved(root / "src"), _resolved(root)]
    tops = {_resolved(root / t) for t in PYTHON_ROOTS}
    d = _resolved(here)
    while d != _resolved(root) and _is_inside(d, root):
        bases.append(d)
        if d in tops:
            break
        d = d.parent
    for base in bases:
        t = _module_at(base, dotted)
        if t is not None and _is_inside(t, root):
            main = t.parent / "__main__.py"
            return _resolved(main) if t.name == "__init__.py" and main.is_file() else t
    return None


def _text_runs(root: Path, here: Path, text: str) -> list[tuple[Path, str]]:
    """(file, the command) for each script a text runs: `python path.py`
    (a path under a tree, or relative to `here`) or `python -m module`."""
    out = []
    for line in text.splitlines():
        for m in MODULE_RUN.finditer(line):
            t = _run_module_target(root, here, m.group(1))
            if t is not None:
                out.append((t, f"-m {m.group(1)}"))
        for m in re.finditer(r"(?<![\w/.-])((?:\./)?[\w./-]+\.py)\b", line):
            if not RUN_PREFIX.search(line[:m.start()]):
                continue
            for base in (root, here):
                q = base / m.group(1)
                if q.is_file() and _is_inside(q, root):
                    out.append((_resolved(q), m.group(1)))
                    break
    return out


def _interpreter_element(e) -> bool:
    """An argv element that names a Python interpreter: `sys.executable`,
    `manifest['python']`, `PYTHON`."""
    text = ast.unparse(e) if not isinstance(e, ast.Starred) else ""
    return "sys.executable" in text or bool(re.search(r"python", text, re.I))


def _argv_runs(root: Path, p: Path, tree) -> list[tuple[Path, str]]:
    """(file, where) for each script an argv in module `p` runs: `[..., '-m',
    'pkg.mod', ...]`, and with a Python interpreter in the argv, the module
    itself through `__file__` (a worker that relaunches itself) or a `.py`
    path beside it (#4093)."""
    rel, out = _rel(root, p), []
    for n in ast.walk(tree):
        if not isinstance(n, (ast.List, ast.Tuple)):
            continue
        consts = [e.value if isinstance(e, ast.Constant) and isinstance(e.value, str) else None for e in n.elts]
        for i, c in enumerate(consts[:-1]):
            if c == "-m" and consts[i + 1]:
                t = _run_module_target(root, p.parent, consts[i + 1])
                if t is not None:
                    out.append((t, f"{rel}:{n.lineno} runs `-m {consts[i + 1]}`"))
        if not any(_interpreter_element(e) for e in n.elts):
            continue
        for e in n.elts:
            if any(isinstance(x, ast.Name) and x.id == "__file__" for x in ast.walk(e)):
                out.append((_resolved(p), f"{rel}:{n.lineno} relaunches itself (`__file__`)"))
            elif isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value.endswith(".py"):
                for base in (p.parent, root):
                    if (base / e.value).is_file():
                        out.append((_resolved(base / e.value), f"{rel}:{n.lineno} runs `{e.value}`"))
                        break
    return out


def controller_run_evidence(root: Path, parsed: dict, index: dict,
                            controllers: dict[str, Path]) -> dict[str, str]:
    """How each run-controller module runs as a script (its `__main__` block
    executes), or no entry when nothing runs it (#4093). Something runs it
    when: an argv in any module runs it (`[python, '-m', module]`, a worker
    relaunching itself through `__file__`); a document beside it, in its
    directory or a parent directory below the top-level tree, or a module
    docstring says `python path.py` or `python -m module`; or no module
    imports it (an entry point: running it is the only way it acts). A
    module a controller only imports is not run by that import."""
    by_path = {_resolved(p): rel for rel, p in controllers.items()}
    how: dict[str, set] = {}
    importers: set[Path] = set()
    for p, (_, tree) in parsed.items():
        for t in _local_import_targets(root, p, tree, index) + _import_targets(root, p, tree, []):
            if _resolved(t) != _resolved(p):
                importers.add(_resolved(t))
        for t, why in _argv_runs(root, p, tree):
            if _resolved(t) in by_path:
                how.setdefault(by_path[_resolved(t)], set()).add(why)
    docs: dict[Path, str] = {}
    tops = {_resolved(root / t) for t in PYTHON_ROOTS}
    for rel, p in controllers.items():
        d = _resolved(p).parent
        while _is_inside(d, root) and d != _resolved(root):
            for md in sorted(d.glob("*.md")):
                if not REGISTERED_COPY.search(_rel(root, md)):
                    docs.setdefault(md, None)
            if d in tops:
                break
            d = d.parent
        doc = ast.get_docstring(parsed[p][1]) or ""
        for t, cmd in _text_runs(root, _resolved(p).parent, doc):
            if t in by_path:
                how.setdefault(by_path[t], set()).add(f"{rel}'s docstring runs `{cmd}`")
    for md in docs:
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigError(f"{_rel(root, md)} cannot be read, so whether it runs a controller is unknown: "
                              f"{exc}") from exc
        for t, cmd in _text_runs(root, md.parent, text):
            if t in by_path:
                how.setdefault(by_path[t], set()).add(f"{_rel(root, md)} runs `{cmd}`")
    for rel, p in controllers.items():
        if _resolved(p) not in importers:
            how.setdefault(rel, set()).add("an entry point: no module imports it")
        for why in _main_block_runs(root, p, parsed, index):
            how.setdefault(rel, set()).add(why)
    return {rel: "; ".join(sorted(v)) for rel, v in sorted(how.items())}


def _is_cli(fn, reached: list) -> bool:
    """A function that is a command-line interface: it, with the module
    functions it calls (`reached`), builds an argparse parser and parses
    arguments, or it is a click command or group."""
    calls = {_dotted(c.func).rsplit(".", 1)[-1] for f in reached for c in ast.walk(f) if isinstance(c, ast.Call)}
    if "ArgumentParser" in calls and calls & {"parse_args", "parse_known_args", "parse_intermixed_args"}:
        return True
    return any(_dotted(d.func if isinstance(d, ast.Call) else d).rsplit(".", 1)[-1] in {"command", "group"}
               for d in fn.decorator_list)


def _main_block_runs(root: Path, p: Path, parsed: dict, index: dict) -> list[str]:
    """Why a module's own `__main__` block says it runs as a script (#4130):
    the block calls a function of the module that starts a run (a native
    launch's argv, the runner's `execute`, in it or in a module function it
    calls), or a command-line interface (an argparse parser it parses, a
    click command) that nothing else calls, in the module or in any module
    that imports it (tests are not read). Such a module acts when a person
    runs it, so another controller importing its helpers does not make it
    "imported only"."""
    tree = parsed[p][1]
    blocks = _main_blocks(tree)
    if not blocks:
        return []
    rel = _rel(root, p)
    defs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    in_block = [(b.lineno, b.end_lineno) for b in blocks]
    called = sorted({c.func.id for b in blocks for c in ast.walk(b)
                     if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in defs})
    out = []
    for name in called:
        # the function and the module functions it calls, to a fixed point
        seen, todo = [], [name]
        while todo:
            f = todo.pop()
            if f in seen:
                continue
            seen.append(f)
            todo += [c.func.id for c in ast.walk(defs[f]) if isinstance(c, ast.Call)
                     and isinstance(c.func, ast.Name) and c.func.id in defs]
        sites = sorted(s for f in seen for s in _launch_sites(root, p, tree, index, defs[f]))
        if sites:
            line, what = sites[0]
            out.append(f"its `__main__` block calls {name}(), which launches a run ({rel}:{line} {what})")
            continue
        if not _is_cli(defs[name], [defs[f] for f in seen]):
            continue
        elsewhere = [f"{rel}:{c.lineno}" for c in ast.walk(tree) if isinstance(c, ast.Call)
                     and isinstance(c.func, ast.Name) and c.func.id == name
                     and not any(a <= c.lineno <= b for a, b in in_block)]
        target = _resolved(p)
        for q, (_, qtree) in parsed.items():
            if q == target:
                continue
            binds = _bindings(root, q, qtree, index)
            for c in ast.walk(qtree):
                if not isinstance(c, ast.Call):
                    continue
                f = c.func
                if (isinstance(f, ast.Name) and binds.get(f.id) == (target, name)) or (
                        isinstance(f, ast.Attribute) and f.attr == name and isinstance(f.value, ast.Name)
                        and binds.get(f.value.id) == (target, None)):
                    elsewhere.append(f"{_rel(root, q)}:{c.lineno}")
        if not elsewhere:
            out.append(f"its `__main__` block calls {name}(), a command-line interface nothing else calls")
    return out


def session_description_lines(text: str) -> list[tuple[int, int, str]]:
    """The lines of a command, agent or skill that Claude Code lists in every
    session (#4091): its frontmatter `name` and `description` (a multi-line
    or block value with its continuation lines), else the first non-empty
    line of the body, which is a command's description when its frontmatter
    gives none (a heading's `#` is dropped there)."""
    lines = text.splitlines()
    start, spans = 0, []
    if lines and lines[0].strip() == "---":
        end = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
        if end is not None:
            for k in range(1, end):
                m = re.match(r"(%s)\s*:" % "|".join(SESSION_KEYS), lines[k])
                if not m:
                    continue
                j = k + 1
                while j < end and (not lines[j].strip() or lines[j][:1] in (" ", "\t")):
                    j += 1
                spans.append((k + 1, j, f"frontmatter {m.group(1)}"))
            if any(label.endswith("description") for *_, label in spans):
                return spans
            start = end + 1
    first = next((k for k in range(start, len(lines)) if lines[k].strip()), None)
    return spans + ([(first + 1, first + 1, "description (the first line)")] if first is not None else [])


def _literal_key(node) -> str | None:
    """The key a subscript or a call argument spells as a string literal."""
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _field_writes(tree, keys, *, appends: bool = False) -> list[tuple[str, ast.AST]]:
    """(key, value) for every value a module writes to a record field whose
    key is a string literal in `keys`, the hook fields Claude Code shows the
    model (#4130, #4142): a dict entry
    (`{'k': v}`), a keyword argument (`dict(k=v)`, `x.update(k=v)`), an item
    assignment, plain, chained or annotated (`x['k'] = v`, `x['k']: T = v`),
    and `x.setdefault('k', v)`; with `appends`, also `x['k'] += v`, whose
    value becomes part of a text field. A key held in a name or built
    (`x[KEY] = v`, `dict(zip(...))`, a list of pairs), an attribute and
    `setattr` are not read."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            out += [(k.value, v) for k, v in zip(n.keys, n.values) if _literal_key(k) in keys]
        elif isinstance(n, ast.keyword) and n.arg in keys:
            out.append((n.arg, n.value))
        elif (isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None) or (
                appends and isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            out += [(t.slice.value, n.value) for t in targets
                    if isinstance(t, ast.Subscript) and _literal_key(t.slice) in keys]
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "setdefault" \
                and len(n.args) == 2 and _literal_key(n.args[0]) in keys:
            out.append((n.args[0].value, n.args[1]))
    return out


def _launch_flag(e) -> str | None:
    """The launch flag an argv element spells: `--system-prompt`,
    `--append-system-prompt`, either with `-file` (#4131), or any of them
    with its value in the same element (`--system-prompt=...`)."""
    if isinstance(e, ast.Constant) and isinstance(e.value, str):
        text = e.value
    elif isinstance(e, ast.JoinedStr) and e.values and isinstance(e.values[0], ast.Constant):
        text = str(e.values[0].value)
    else:
        return None
    if text in LAUNCH_FLAGS:
        return text
    head = text.split("=", 1)[0]
    return head if "=" in text and head in LAUNCH_FLAGS else None


def _parents(tree) -> dict[int, ast.AST]:
    """Each node's parent in a module, keyed by the child's id."""
    out: dict[int, ast.AST] = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            out[id(c)] = n
    return out


def _handed_on(node, parents: dict) -> tuple[str, ast.AST | None] | None:
    """How an expression is handed on whole to code its function does not
    run itself (#4156): a direct argument of a call (positional and not
    starred, or a keyword's value), with the call; a value the function
    returns or yields, with None (`yield from` hands on its elements, not
    the list). None for anything else."""
    up = parents.get(id(node))
    if isinstance(up, ast.keyword) and up.value is node:
        call = parents.get(id(up))
        return (f"passed to `{ast.unparse(call.func)}`", call) if isinstance(call, ast.Call) else None
    if isinstance(up, ast.Call) and any(a is node for a in up.args):
        return f"passed to `{ast.unparse(up.func)}`", up
    if isinstance(up, ast.Return) and up.value is node:
        return "returned", None
    if isinstance(up, ast.Yield) and up.value is node:
        return "yielded", None
    return None


def _value_unkept(call, parents: dict) -> str | None:
    """Where a call's value is not kept (#4156): a statement of its own, also
    awaited, or a `with` item, whose value is a context manager and never a
    list. None where something keeps it: there the call may be what builds
    the list that is launched (`argv = list([...])`)."""
    up = parents.get(id(call))
    if isinstance(up, ast.Await):
        call, up = up, parents.get(id(up))
    if isinstance(up, ast.Expr) and up.value is call:
        return "a call made as a statement"
    if isinstance(up, ast.withitem) and up.context_expr is call:
        return "a `with` item"
    return None


_OPERATORS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.MatMult: "@", ast.Div: "/", ast.FloorDiv: "//",
              ast.Mod: "%", ast.Pow: "**", ast.LShift: "<<", ast.RShift: ">>", ast.BitOr: "|", ast.BitXor: "^",
              ast.BitAnd: "&"}


def _use(node, parents: dict) -> str:
    """What the code around an expression does with it, in words: the
    reason a launch is not shown to pass a flag (#4156)."""
    up = parents.get(id(node))
    if isinstance(up, ast.BinOp):
        return f"an operand of `{_OPERATORS.get(type(up.op), type(up.op).__name__)}`, which builds another value"
    if isinstance(up, ast.BoolOp):
        return f"an operand of `{'and' if isinstance(up.op, ast.And) else 'or'}`"
    if isinstance(up, ast.Starred):
        return "a starred element, spread into another value"
    if isinstance(up, ast.Attribute):
        called = isinstance(parents.get(id(up)), ast.Call) and parents[id(up)].func is up
        return f"the object of `.{up.attr}{'()' if called else ''}`"
    if isinstance(up, ast.Subscript):
        return "subscripted" if up.value is node else "a subscript"
    if isinstance(up, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
        return f"an element of a {type(up).__name__.lower()}"
    if isinstance(up, ast.comprehension):
        return "iterated by a comprehension"
    if isinstance(up, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        return "the element of a comprehension"
    if isinstance(up, ast.For):
        return "iterated by a `for` loop"
    if isinstance(up, ast.IfExp):
        return "a branch of a conditional expression"
    if isinstance(up, ast.NamedExpr):
        return "bound by `:=`"
    if isinstance(up, (ast.Assign, ast.AnnAssign)):
        return "bound to another name (an alias)"
    if isinstance(up, ast.AugAssign):
        return "the value of an augmented assignment"
    if isinstance(up, ast.Lambda):
        return "the value of a lambda"
    if isinstance(up, ast.YieldFrom):
        return "handed on element by element by `yield from`"
    return f"used in `{ast.unparse(up)[:60]}`" if up is not None else "used"


def _reads(node, parents: dict) -> bool:
    """A use that only reads a list: an operand of a comparison
    (`'--x' in argv`) or a value formatted into a string (#4156)."""
    return isinstance(parents.get(id(node)), (ast.Compare, ast.FormattedValue))


def _scope_of(node, parents: dict):
    """The innermost function or class whose body holds `node`, or None at
    module level."""
    up = parents.get(id(node))
    while up is not None and not isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        up = parents.get(id(up))
    return up


def _rebinding(n, name: str, fn) -> str | None:
    """How a node binds `name` other than through an `ast.Name` (which
    carries its own context): a parameter of a nested function or lambda,
    `except ... as`, an import, a nested definition, `global` or
    `nonlocal`, a match capture. The function's own parameters bind before
    its body runs and are not counted."""
    if isinstance(n, ast.arg) and n.arg == name:
        own = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs + [fn.args.vararg, fn.args.kwarg]
        return None if any(n is a for a in own) else "a parameter of a nested function"
    if isinstance(n, ast.ExceptHandler) and n.name == name:
        return "bound by `except ... as`"
    if isinstance(n, ast.alias) and (n.asname or n.name.split(".")[0]) == name:
        return "bound by an import"
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn and n.name == name:
        return "bound by a nested definition"
    if isinstance(n, (ast.Global, ast.Nonlocal)) and name in n.names:
        return f"declared `{type(n).__name__.lower()}`"
    if isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name == name or \
            isinstance(n, ast.MatchMapping) and n.rest == name:
        return "bound by a `match` pattern"
    return None


def _holder_shown(rel: str, parents: dict, assign) -> tuple[bool, list[str]]:
    """Whether the name, attribute or item a plain or annotated assignment
    binds an argv list to holds that list, unchanged, wherever its function
    hands it on (#4156). Shown only for one target, in a function, that is a
    name or an attribute or literal-key item of a name (`argv`, `self.argv`,
    `job['argv']`), where every other occurrence of it in the function
    (nested functions and classes included) hands it on whole (a direct
    argument of a call, a returned or yielded value) or only reads it (a
    comparison, an f-string). For an attribute or item, the name that holds
    it is held to the same rule. Anything else, a binding, a deletion or a
    use of any other kind, is a reason it is not shown."""
    at = f"{rel}:{assign.lineno}"
    targets = assign.targets if isinstance(assign, ast.Assign) else [assign.target]
    if len(targets) != 1:
        return False, [f"{at} the argv list is bound to {len(targets)} targets at once"]
    target = targets[0]
    held = ast.unparse(target)
    fn = _scope_of(assign, parents)
    if fn is None:
        return False, [f"{at} the argv `{held}` is bound at module level, where every module that imports it "
                       "can change it"]
    if isinstance(fn, ast.ClassDef):
        return False, [f"{at} the argv `{held}` is bound in a class body, where the class and its instances can "
                       "change it"]
    if isinstance(target, ast.Name):
        base, part = target.id, None
    elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
        base, part = target.value.id, ("attribute", target.attr)
    elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and \
            isinstance(target.slice, ast.Constant) and type(target.slice.value) in (str, int):
        base, part = target.value.id, ("item", target.slice.value)
    else:
        return False, [f"{at} the argv list is held by `{held}`, which cannot be resolved"]

    def is_holder(x) -> bool:
        if part is None or not isinstance(x, (ast.Attribute, ast.Subscript)) or not \
                (isinstance(x.value, ast.Name) and x.value.id == base):
            return False
        if part[0] == "attribute":
            return isinstance(x, ast.Attribute) and x.attr == part[1]
        return isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Constant) and \
            type(x.slice.value) is type(part[1]) and x.slice.value == part[1]

    problems, uses = [], []
    for n in ast.walk(fn):
        how = _rebinding(n, base, fn)
        if how is not None:
            problems.append(f"{rel}:{getattr(n, 'lineno', assign.lineno)} `{base}` is {how}")
            continue
        if not isinstance(n, ast.Name) or n.id != base or n is target or (part is not None and n is target.value):
            continue
        x, what = n, f"`{held}`"
        if part is not None:
            up = parents.get(id(n))
            if is_holder(up):
                x = up
            else:
                what = f"`{base}`, which holds the argv,"
        if isinstance(x.ctx, ast.Store):
            problems.append(f"{rel}:{x.lineno} {what} is assigned again")
        elif isinstance(x.ctx, ast.Del):
            problems.append(f"{rel}:{x.lineno} {what} is deleted")
        elif (h := _handed_on(x, parents)) is not None:
            uses.append(f"line {x.lineno}: {what.strip(',')} {h[0]}")
        elif _reads(x, parents):
            uses.append(f"line {x.lineno}: {what.strip(',')} read")
        else:
            problems.append(f"{rel}:{x.lineno} {what} is {_use(x, parents)}")
    if problems:
        return False, problems
    return True, [f"{at} the argv list is bound to `{held}` as it is, which the function otherwise only hands on "
                  "whole or reads (" + ("; ".join(uses) or "no other use") + ")"]


def _argv_shown(rel: str, parents: dict, lst) -> tuple[bool, list[str]]:
    """Whether a launch's argv list literal is, unchanged, the list its
    function hands over (#4156): the call's argument itself, in a call
    nothing keeps the value of (`subprocess.run([...])`, `with
    Popen([...]) as p:`); returned or yielded as it is; or the whole value
    of a plain or annotated assignment to a holder its function never
    changes (`_holder_shown`). (True, how) or (False, why not)."""
    at = f"{rel}:{lst.lineno}"
    handed = _handed_on(lst, parents)
    if handed is not None:
        how, call = handed
        if call is None:
            return True, [f"{at} the argv list is {how} as it is"]
        where = _value_unkept(call, parents)
        if where is None:
            return False, [f"{at} the argv list is {how}, whose value is kept, so that call can be what builds the "
                           "list launched (`argv = list([...])`)"]
        return True, [f"{at} the argv list is {how} as it is, in {where}"]
    up = parents.get(id(lst))
    if isinstance(up, (ast.Assign, ast.AnnAssign)) and up.value is lst:
        return _holder_shown(rel, parents, up)
    return False, [f"{at} the argv list is {_use(lst, parents)}"]


def _flags_shown(rel: str, lst, flags: frozenset, named: str, shown: bool, how: list[str]) -> tuple:
    """(True | False | None, evidence) for one flag set in one launch
    (#4156): True only where a literal element of the argv list is a flag
    and the list is shown to be what the launch hands over; False where it
    is shown and holds neither such a literal nor a starred element; None
    otherwise. A starred element (`*CLI_FLAGS`, `*overlay['cli_flags']`) is
    never followed: a name or field can hold anything by the time the list
    is built."""
    lits = sorted({f"{rel}:{e.lineno} {e.value}" for e in lst.elts
                   if isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value in flags})
    stars = [e for e in lst.elts if isinstance(e, ast.Starred)]
    loose = (ast.BinOp, ast.BoolOp, ast.IfExp, ast.Compare, ast.UnaryOp, ast.Lambda, ast.NamedExpr, ast.Await)
    spread = [f"{rel}:{lst.lineno} no element of the argv list is the literal {named}; its starred elements ("
              + ", ".join("`*" + (f"({ast.unparse(s.value)})" if isinstance(s.value, loose) else ast.unparse(s.value))
                          + "`" for s in stars) + ") are not followed"] if stars else []
    if not shown:
        return None, how + ([] if lits else spread)
    if lits:
        return True, lits + how
    if spread:
        return None, spread
    return False, [f"{rel}:{lst.lineno} no element of the argv list is the literal {named}"]


def launch_flags(controllers: dict[str, Path], parsed: dict) -> list[dict]:
    """Whether each registered native launch is shown to switch off what an
    interactive session loads (#4092, #4131, #4156). A launch is a list or
    tuple literal in a run controller that holds `--system-prompt`,
    `--append-system-prompt` or either's `-file` form (also as
    `--flag=value`). Each is read twice: `carries`, whether it passes
    `--safe-mode`, which switches off every session customization
    (CLAUDE.md, hooks, commands, agents, skills); and `memory_off`, whether
    it passes `--safe-mode` or `--bare`, which switches off CLAUDE.md and
    the settings hooks (`--bare` leaves skills resolving, so it does not
    switch the command, agent and skill descriptions off).

    Sound by construction rather than by a list of the ways a flag can be
    dropped (#4156): a flag is shown only where it is a literal element of
    that list and the list is shown to be what the function hands over,
    unchanged (`_argv_shown`). Nothing the list is built from is followed:
    a starred element, a name, a module constant, an imported constant or a
    record field is "not shown" (`None`), as is a list built any other way
    (a concatenation, a comprehension, a value wrapped in a call) or held
    by a holder used any other way. What the code the list is handed to
    does with it (a callee, a caller) is not read. A launch flag outside a
    list or tuple literal is a launch whose flags cannot be read. Returns
    one row per launch: its site, `carries` and `memory_off` (True, False
    or None) and the evidence or the reasons for each."""
    rows = []
    for crel, p in sorted(controllers.items()):
        tree = parsed[p][1]
        parents = _parents(tree)
        read = set()
        for n in ast.walk(tree):
            if not isinstance(n, (ast.List, ast.Tuple)):
                continue
            flag_node = next((e for e in n.elts if _launch_flag(e)), None)
            if flag_node is None:
                continue
            read.update(id(v) for v in ast.walk(flag_node))
            shown, how = _argv_shown(crel, parents, n)
            row = {"site": f"{crel}:{flag_node.lineno} {_launch_flag(flag_node)}"}
            for key, flags, named in (("carries", frozenset({SAFE_MODE}), "`--safe-mode`"),
                                      ("memory_off", MEMORY_OFF_FLAGS, "`--safe-mode` or `--bare`")):
                ok, ev = _flags_shown(crel, n, flags, named, shown, how)
                row[key] = ok
                row["evidence" if key == "carries" else "memory_evidence"] = ev
            rows.append(row)
        # a launch flag outside an argv list (appended, or in a set) is a
        # launch whose flags cannot be read: never assumed to carry one
        for n in ast.walk(tree):
            flag = _launch_flag(n) if isinstance(n, (ast.Constant, ast.JoinedStr)) else None
            if flag and id(n) not in read:
                why = [f"{crel}:{n.lineno} `{flag}` is not in an argv list, so the launch's flags cannot be read"]
                rows.append({"site": f"{crel}:{n.lineno} {flag}", "carries": None, "evidence": why,
                             "memory_off": None, "memory_evidence": why})
    return sorted(rows, key=lambda r: r["site"])


# ---- text a model receives, by data flow (#4054)


def _function_defs(tree) -> dict[str, ast.AST]:
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(n.name, n)
    return out


def _module_assignments(tree) -> dict[str, ast.AST]:
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n
        elif isinstance(n, ast.AnnAssign) and n.value is not None and isinstance(n.target, ast.Name):
            out[n.target.id] = n
    return out


def _writes_name(target, name: str) -> bool:
    """Whether an assignment target writes the name, or the object a name
    holds: `NAME`, `A, NAME`, `*NAME`, `NAME[k]`, `NAME.x`, `NAME[k].x`."""
    if isinstance(target, ast.Name):
        return target.id == name
    if isinstance(target, (ast.Tuple, ast.List)):
        return any(_writes_name(e, name) for e in target.elts)
    if isinstance(target, ast.Starred):
        return _writes_name(target.value, name)
    while isinstance(target, (ast.Subscript, ast.Attribute)):
        target = target.value
    return isinstance(target, ast.Name) and target.id == name


def _constant_writes(tree, name: str) -> list[tuple[ast.stmt, list[ast.AST]]]:
    """Every statement at the top of a module that writes the module
    constant `name`, with the expressions whose values become part of it
    (#4156): an assignment to it, plain (also unpacked or chained),
    annotated or augmented (`NAME += ...`), or to an item or attribute of it
    (`NAME[k] = v`), and its value; a method call on it made as a statement
    (`NAME.append(v)`), and its arguments. A write inside a block (`if`,
    `try`) or a function is not read."""
    out = []
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and stmt.value is not None:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if any(_writes_name(t, name) for t in targets):
                out.append((stmt, [stmt.value]))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and \
                isinstance(stmt.value.func, ast.Attribute) and _writes_name(stmt.value.func.value, name):
            call = stmt.value
            out.append((stmt, [a.value if isinstance(a, ast.Starred) else a for a in call.args]
                        + [k.value for k in call.keywords]))
    return out


def _params(fn) -> list[str]:
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    return names + [x.arg for x in (a.vararg, a.kwarg) if x is not None]


def _local_assignments(fn) -> dict[str, list[ast.AST]]:
    out: dict[str, list] = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
                        out.setdefault(x.id, []).append(n.value)
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)) and n.value is not None and isinstance(n.target, ast.Name):
            out.setdefault(n.target.id, []).append(n.value)
    return out


def _innermost_function(tree, line: int):
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno <= line <= n.end_lineno:
            if best is None or n.lineno >= best.lineno:
                best = n
    return best


def model_text_spans(root: Path, parsed: dict, index: dict,
                     controllers: dict[str, Path]) -> dict[str, list[tuple[int, int, str]]]:
    """Code whose text a run controller hands a model, found by data flow as
    well as by name (#4054). Seeds: the controller functions a name says
    render model text (`MODEL_TEXT_FUNCTION`), every argv element that
    follows `--system-prompt` or `--append-system-prompt` in a controller,
    and every value a controller gives a hook field Claude Code shows the
    model (`permissionDecisionReason`, the PreToolUse deny reason, and
    `additionalContext`, #4130) under a literal key: a dict entry, a keyword
    argument, an item assignment (plain, annotated or `+=`) or
    `.setdefault()` (`_field_writes`, #4142). From an element or a
    function's return values, the flow is followed through local
    assignments: a literal that becomes part of the text is model text, a
    function whose result does is model text (and its returns are followed
    in turn, across modules through imports), and a module constant the text
    is built from (`SYSTEM`, returned by `render_system`) is model text,
    with every statement at the top of its module that writes it, and all
    that statement's value is built from in turn, recursively and each
    constant once: the constants it names, of its module or imported by
    name (`POLICY` in `SYSTEM = POLICY + '...'`, #4156), the functions
    whose results become part of it, and its literals. A call's arguments
    are followed for the constants they pass, not for the functions that
    compute them.

    A hook field built from a parameter (`hook_output(classification,
    basis)`), directly or through the function's locals, is fed by
    classifier pairs that reach it through threads and queues no data flow
    follows. Those pairs are found by their decision
    instead: every controller function that returns a tuple whose decision
    element is a literal the hook function compares its decision parameter
    with (`'prescribed'`), widened to a fixed point by the other decisions
    such functions return (`'not_prescribed'`); the element in the position
    of the reason parameter is model text. Returns path -> (first, last,
    label)."""
    defs_of, consts_of, binds_of = {}, {}, {}

    def defs(q):
        if q not in defs_of:
            defs_of[q] = _function_defs(parsed[q][1])
        return defs_of[q]

    def consts(q):
        if q not in consts_of:
            consts_of[q] = _module_assignments(parsed[q][1])
        return consts_of[q]

    def binds(q):
        if q not in binds_of:
            binds_of[q] = _bindings(root, q, parsed[q][1], index)
        return binds_of[q]

    spans: dict[Path, dict[tuple[int, int], str]] = {}
    literals: dict[Path, dict[tuple[int, int], str]] = {}
    marked: set[tuple] = set()
    todo: list[tuple] = []

    def mark_function(q, name, why):
        if q not in parsed or name not in defs(q) or (q, name) in marked:
            return
        marked.add((q, name))
        fn = defs(q)[name]
        spans.setdefault(q, {}).setdefault((fn.lineno, fn.end_lineno), f"{name}() ({why})")
        todo.append((q, name))

    def mark_constant(q, name, why):
        """A module constant the text is built from is model text, and so is
        all it is built from (#4156): each statement at the top of its
        module that writes it (`_constant_writes`) is marked, and what that
        statement puts in it is followed as model text in turn: the
        constants it names (of its module, or imported by name), each marked
        the same way, recursively; the functions whose results become part
        of it; its literals. Each constant once, so a cycle ends."""
        if q not in parsed or name not in consts(q) or ("constant", q, name) in marked:
            return
        marked.add(("constant", q, name))
        for stmt, values in _constant_writes(parsed[q][1], name):
            spans.setdefault(q, {}).setdefault((stmt.lineno, stmt.end_lineno), f"{name} ({why})")
            flow(q, None, values, f"part of {name}, {why}")

    def callee(q, f):
        if isinstance(f, ast.Name):
            if f.id in defs(q):
                return q, f.id
            target, attr = binds(q).get(f.id, (None, None))
            if target is not None and attr and target in parsed and attr in defs(target):
                return target, attr
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            target, attr = binds(q).get(f.value.id, (None, None))
            if target is not None and attr is None and target in parsed and f.attr in defs(target):
                return target, f.attr
        return None

    def flow(q, fn, exprs, why):
        local = _local_assignments(fn) if fn is not None else {}
        params = set(_params(fn)) if fn is not None else set()
        seen: set[tuple] = set()
        where = f"text in {fn.name}()" if fn is not None else "module text"

        def walk(e, mode):
            if e is None or (id(e), mode) in seen:
                return
            seen.add((id(e), mode))
            if mode == "text" and (isinstance(e, ast.JoinedStr) or (
                    isinstance(e, ast.Constant) and isinstance(e.value, str))):
                # a literal that becomes part of the text (#4130)
                literals.setdefault(q, {}).setdefault((e.lineno, e.end_lineno), f"{where} ({why})")
            if isinstance(e, ast.Name):
                if e.id in local:
                    for v in local[e.id]:
                        walk(v, mode)
                elif e.id not in params:
                    if e.id in consts(q):
                        mark_constant(q, e.id, why)
                    else:
                        target, attr = binds(q).get(e.id, (None, None))
                        if target is not None and attr:
                            mark_constant(target, attr, why)
                return
            if isinstance(e, ast.Call):
                text_args = isinstance(e.func, ast.Attribute) and e.func.attr in STR_TEXT_METHODS
                if mode == "text":
                    hit = callee(q, e.func)
                    if hit is not None:
                        mark_function(hit[0], hit[1], why)
                if isinstance(e.func, ast.Attribute):
                    walk(e.func.value, mode)
                for a in e.args:
                    walk(a.value if isinstance(a, ast.Starred) else a, mode if text_args else "data")
                for k in e.keywords:
                    walk(k.value, "data")
                return
            if isinstance(e, ast.IfExp):
                walk(e.body, mode)
                walk(e.orelse, mode)
                return
            if isinstance(e, (ast.Compare, ast.Lambda)):
                return
            for child in ast.iter_child_nodes(e):
                walk(child, mode)

        for e in exprs:
            walk(e, "text")

    hook_sinks = []
    for rel, p in sorted(controllers.items()):
        tree = parsed[p][1]
        for name, fn in defs(p).items():
            if MODEL_TEXT_FUNCTION.match(name):
                mark_function(p, name, "renders model text")
        # every way `writers()` reads a record field, and `+=` (#4142)
        hook_sinks += [(p, k, v) for k, v in _field_writes(tree, HOOK_MODEL_FIELDS, appends=True)]
        for n in ast.walk(tree):
            if not isinstance(n, (ast.List, ast.Tuple)):
                continue
            for i, e in enumerate(n.elts):
                flag = _launch_flag(e)
                if flag not in SYSTEM_PROMPT_FLAGS:
                    continue
                # the prompt is the next element, or the value an `=` spelling carries
                sink = e if not (isinstance(e, ast.Constant) and e.value == flag) else \
                    n.elts[i + 1] if i + 1 < len(n.elts) else None
                if sink is None:
                    continue
                why = f"passed to {flag} at {rel}:{e.lineno}"
                if isinstance(sink, (ast.Constant, ast.JoinedStr)):
                    spans.setdefault(p, {}).setdefault((sink.lineno, sink.end_lineno), why)
                flow(p, _innermost_function(tree, sink.lineno), [sink], why)
    # hook fields the model is shown (#4130), and the classifier pairs that
    # feed one built from its function's parameters
    for p, field_name, value in hook_sinks:
        tree = parsed[p][1]
        fn = _innermost_function(tree, value.lineno)
        why = f"{field_name} at {_rel(root, p)}:{value.lineno}"
        flow(p, fn, [value], why)
        if fn is None:
            continue
        # the pair a classifier returns lines up with the hook function's own
        # parameters (`hook_output(classification, basis)`), a method's
        # `self` aside
        params = [x for x in _params(fn) if x not in {"self", "cls"}]
        reasons = _reaching_params(fn, value, params)
        decisions: dict[str, set] = {}
        for left, op, right in _compares(fn):
            if not isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)):
                continue
            for side, other in ((left, right), (right, left)):
                if isinstance(side, ast.Name) and side.id in params and side.id not in reasons:
                    lits = [x.value for x in ast.walk(other) if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                    decisions.setdefault(side.id, set()).update(lits)
        for reason in sorted(reasons):
            for decision, vocab in sorted(decisions.items()):
                ri, di = params.index(reason), params.index(decision)
                found = _classifier_pairs(controllers, parsed, ri, di, set(vocab))
                label = f"the reason it returns reaches {fn.name}()'s {why}"
                for q, cfn, exprs in found:
                    flow(q, cfn, exprs, label)
    while todo:
        q, name = todo.pop()
        fn = defs(q)[name]
        returns = [r.value for r in ast.walk(fn) if isinstance(r, ast.Return) and r.value is not None]
        flow(q, fn, returns, f"its value reaches {name}()")
    # a literal inside a span already found adds nothing
    for q, sp in literals.items():
        for (a, b), label in sp.items():
            if not any(lo <= a and b <= hi for lo, hi in spans.get(q, {})):
                spans.setdefault(q, {}).setdefault((a, b), label)
    return {_rel(root, q): sorted((a, b, label) for (a, b), label in sp.items())
            for q, sp in spans.items() if _is_inside(q, root)}


def _reaching_params(fn, value, params: list[str]) -> set[str]:
    """The parameters of `fn` that `value` is built from, directly or
    through the function's local assignments (`reason = '...' + basis`, then
    the field set to `reason`, #4142)."""
    local, out, seen, todo = _local_assignments(fn), set(), set(), [value]
    while todo:
        for x in ast.walk(todo.pop()):
            if not isinstance(x, ast.Name):
                continue
            if x.id in params:
                out.add(x.id)
            elif x.id in local and x.id not in seen:
                seen.add(x.id)
                todo += local[x.id]
    return out


def _classifier_pairs(controllers: dict[str, Path], parsed: dict, reason_at: int, decision_at: int,
                      vocab: set) -> list[tuple[Path, ast.AST, list]]:
    """(module, function, reason expressions) of every controller function
    that returns a decision pair whose decision is in `vocab`, widened to a
    fixed point by the other decisions such functions return (#4130): a
    classifier whose reason feeds a hook field the model is shown."""
    funcs = [(p, fn) for p in sorted(set(controllers.values())) for fn in ast.walk(parsed[p][1])
             if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))]

    def pairs(fn):
        width = max(reason_at, decision_at)
        return [r.value for r in ast.walk(fn) if isinstance(r, ast.Return) and isinstance(r.value, ast.Tuple)
                and len(r.value.elts) > width]

    found: dict[int, tuple] = {}
    grew = True
    while grew:
        grew = False
        for p, fn in funcs:
            ps = pairs(fn)
            decided = {t.elts[decision_at].value for t in ps if isinstance(t.elts[decision_at], ast.Constant)
                       and isinstance(t.elts[decision_at].value, str)}
            if not decided & vocab:
                continue
            if id(fn) not in found:
                found[id(fn)] = (p, fn, [t.elts[reason_at] for t in ps])
                grew = True
            if decided - vocab:
                vocab |= decided
                grew = True
    return sorted(found.values(), key=lambda x: (str(x[0]), x[1].lineno))


def discover(root: Path) -> tuple[Surfaces, dict]:
    s = Surfaces()
    facts: dict = {"python": f"{platform.python_implementation()} {platform.python_version()}"}
    src = root / "src/data_sheets_schema"
    prompts_dir = root / "src/download/prompts"

    # ---- every non-test Python module under PYTHON_ROOTS, parsed once
    # (#4023). One that does not parse stops the scan (#4092): discovery
    # cannot vouch that it is not a controller, a launcher or a model client.
    sources, skipped, nested_memory = _walk_sources(root)
    facts["python_roots"] = list(PYTHON_ROOTS)
    facts["python_sources"] = [_rel(root, p) for p in sources]
    facts["registered_copies_skipped"] = skipped
    parsed, unparsed = {}, []
    for p in sources:
        text, tree = _parse(p)
        if tree is None:
            unparsed.append(f"{_rel(root, p)} ({_parse_problem(p)})")
        else:
            parsed[p] = (text, tree)
    if unparsed:
        raise _unparsed(unparsed)
    index = _notes_index(root, parsed)

    # ---- api: runner closure, conditions, evidence protocols
    api_closure = _package_closure(root, ["data_sheets_schema.cli.api", "data_sheets_schema.api_runner"])
    facts["api_closure"] = [_rel(root, p) for p in api_closure]
    for p in api_closure:
        s.add(_rel(root, p), "api", _module_role(p), "live", "import closure of cli/api.py + api_runner", runs=False)
    cond = condition_table(root)
    gh = github_assistant_run(root, cond)
    if gh:
        cond["live"] = sorted(set(cond["live"]) | {gh["condition_name"]})
    facts["conditions"] = cond
    facts["github_assistant_run"] = gh
    for name, rel in sorted(cond["prompts"].items()):
        status = "live" if name in cond["live"] else "historical"
        s.add(rel, "api", "model_facing", status, f"condition prompt `{name}`")
    tuned = cond["tuned"]
    if tuned:
        if tuned["sends_tuned_prompt"]:
            s.add(cond["tuned_prompt"], "api", "model_facing", "historical", "condition `tuned`: resolve_prompt "
                  "sends its text")
        else:
            s.add(cond["tuned_prompt"], "api", "run_shaping", "historical", "condition `tuned`: hashed "
                  "(prompt_files) and named in a header line; resolve_prompt never sends its text (#4058)")
        for p in sorted((root / cond["components"]).glob("*.md")):
            if p.name.lower() == "readme.md":
                s.add(_rel(root, p), "api", "run_shaping", "historical", "components README")
            else:
                s.add(_rel(root, p), "api", "model_facing" if tuned["sends_components"] else "run_shaping",
                      "historical", "condition `tuned` component: resolve_prompt inserts "
                      + ", ".join(tuned["appends"]))
    protocols = sorted(prompts_dir.glob("evidence_protocol_v*.md"),
                       key=lambda p: int(re.search(r"_v(\d+)", p.name).group(1)))
    for i, p in enumerate(protocols):
        s.add(_rel(root, p), "api", "model_facing",
              "live" if i == len(protocols) - 1 else "historical", "evidence protocol")
    pinned = yaml.safe_load((prompts_dir / "canonical_hashes.yaml").read_text(encoding="utf-8"))
    facts["pinned_prompts"] = sorted((pinned or {}).get("files", {}))
    for rel in facts["pinned_prompts"]:
        if (root / rel).exists() and rel not in s.files:
            s.add(rel, "api", "model_facing", "historical", "pinned prompt file")
    s.add("src/download/prompts/canonical_hashes.yaml", "api", "run_shaping", "live", "prompt pin registry")
    for p in sorted(prompts_dir.glob("determinism_settings.yaml")):
        s.add(_rel(root, p), "api", "run_shaping", "live", "determinism settings")

    # ---- what a native run is handed (#4054)
    toolchain = derive_toolchain(root)
    facts["toolchain"] = toolchain

    # ---- the native playbook's CLI groups, before the arms and the
    # controllers: a module in a generation closure is neither an arm
    # command nor a launcher
    playbook = root / PLAYBOOK
    starts = ["data_sheets_schema.agentic_runtime"] + [
        f"data_sheets_schema.cli.{g}" for g in _cli_groups(root, playbook.read_text(encoding="utf-8"))]
    early_native = _package_closure(root, sorted(set(starts)))

    # ---- upstream input and the deterministic arms (#4054)
    shared = shared_input_modules(root)
    facts["shared_input"] = shared
    stop = {_resolved(root / r) for r in shared}
    arm_commands = deterministic_arm_commands(root, frozenset(_rel(root, p) for p in api_closure + early_native))
    det_closure, det_dirs = _code_closure(root, [root / r for r in arm_commands], stop=stop)
    facts["deterministic_commands"] = arm_commands
    facts["deterministic_closure"] = [_rel(root, p) for p in det_closure]
    facts["deterministic_sys_path"] = det_dirs
    exclude = frozenset(_rel(root, p) for p in api_closure + early_native + det_closure)

    # ---- run controllers and launchers (#4023, #4054): what they do, not a
    # glob. A controller module runs as a script only where something runs it
    # (#4093): an import by another controller never runs its __main__ block.
    controllers, controller_why, evaluation_reached = run_controllers(root, parsed, index, exclude)
    controller_runs = controller_run_evidence(root, parsed, index, controllers)
    facts["controllers"] = controller_why
    facts["controller_runs"] = {rel: controller_runs.get(rel, "") for rel in controller_why}
    for rel in controller_why:
        s.add(rel, "run_controllers", "run_shaping", "live", "run controller: " + controller_why[rel],
              runs=rel in controller_runs)
    controller_text = {}
    for rel, p in sorted(controllers.items()):
        for name in _md_literals(parsed[p][1]):
            md = p.parent / name
            if md.is_file():
                controller_text.setdefault(_rel(root, md), rel)
    facts["controller_text"] = controller_text
    for rel, by in sorted(controller_text.items()):
        s.add(rel, "run_controllers", "model_facing", "live", f"text a controller hands to the model ({by})")

    # ---- every playbook, agent and file that a playbook, an agent, a live
    # prompt, a controller, the assistant workflow or an instruction it loads
    # names or runs (#4023, #4054, #4091, #4093)
    walker = (lambda d: d.rglob(toolchain["pattern"])) if toolchain["recursive"] else \
        (lambda d: d.glob(toolchain["pattern"]))
    claude_files = sorted({p for d in toolchain["directories"] for p in walker(root / d) if p.is_file()})
    claude_set = {_rel(root, p) for p in claude_files}
    claude_names = {p.stem: _rel(root, p) for p in claude_files if p.stem.lower() != "readme"}
    playbooks = [p for p in claude_files if p.parent == root / ".claude/commands" and p.name.startswith("d4d-")]
    wf = root / ".github/workflows"
    workflow = wf / "d4d-agent.yml"
    assistant_set = {_rel(root, p) for p in sorted(wf.glob("d4d_assistant_*.md"))}
    memory = [rel for rel in PROJECT_MEMORY if (root / rel).is_file()] + \
        [rel for rel in nested_memory if rel not in PROJECT_MEMORY]
    memory_set = set(memory)
    referenced: set[str] = set()
    named: dict[str, dict] = {}
    memory_named_by: set[str] = set()
    loaders: dict[str, set] = {}
    run_scripts: dict[str, dict] = {}
    cli_groups: dict[str, dict] = {}
    queue: list[tuple[str, str, str, str, str]] = []
    done: set[tuple[str, str, str]] = set()

    def names_in(text: str, namer: str, approach: str, role: str, status: str, claude_only: bool = False,
                 namer_kind: str = "text", groups: bool = True):
        """Follow what a text names. A text the model reads (`namer_kind`
        "text") hands the model the text files it names, raw (#4091); code
        (the workflow) hands a model only the instructions (.md, .txt) it
        names, and reads the rest as data. A `.py` it runs is followed
        through its imports, and a CLI group it runs through the group's."""
        for rel, run in _named_files(root, text, claude_names).items():
            if rel == namer:
                continue
            if rel in memory_set:
                memory_named_by.add(namer)
                continue
            if rel in claude_set:
                if role != "exposed" and rel not in referenced:
                    referenced.add(rel)
                    queue.append((rel, "native_agentic", "model_facing", "live", namer))
                continue
            if claude_only:
                continue
            entry = named.setdefault(rel, {"by": set(), "runs": False, "approaches": set()})
            entry["by"].add(namer)
            entry["runs"] = entry["runs"] or run
            entry["approaches"].add(approach)
            if rel in assistant_set:
                loaders.setdefault(rel, set()).add(f"{namer} ({approach})")
                queue.append((rel, approach, "exposed" if role == "exposed" else "model_facing", status, namer))
                continue
            # text a named file holds is read by the model; code it runs shapes the run
            texts = NAMED_TEXT if namer_kind == "text" else frozenset({".md", ".txt"})
            kind = "exposed" if role == "exposed" else "model_facing" if Path(rel).suffix in texts else "run_shaping"
            s.add(rel, approach, kind, status, f"named by {namer}" + (", which runs it" if run else ""),
                  runs=run, raw=kind == "model_facing")
            if run and rel.endswith(".py") and rel not in CLI_PACKAGE:
                by = run_scripts.setdefault(rel, {})
                by[approach] = "run_shaping" if role != "exposed" or by.get(approach) == "run_shaping" else "exposed"
        if groups and not claude_only:
            for g in _cli_groups(root, text):
                by = cli_groups.setdefault(approach, {}).setdefault(g, {})
                by[namer] = "exposed" if role == "exposed" else "run_shaping"

    def drain():
        while queue:
            rel, approach, role, status, namer = queue.pop()
            if (rel, approach, role) in done:
                continue
            done.add((rel, approach, role))
            if rel in assistant_set:
                s.add(rel, approach, role, status, f"assistant instruction file {namer} loads",
                      raw=role == "model_facing")
            names_in((root / rel).read_text(encoding="utf-8"), rel, approach, role, status)

    queue += [(_rel(root, p), "native_agentic", "model_facing", "live", "slash command") for p in playbooks]
    for c in cond["live"]:          # an API prompt can only point at a playbook (#4014)
        names_in((root / cond["prompts"][c]).read_text(encoding="utf-8"), cond["prompts"][c], "native_agentic",
                 "model_facing", "live", claude_only=True)
    # a controller's CLI groups are not followed here: the package modules
    # the controllers import are, through the native closure below
    for rel, by in sorted(controller_text.items()):
        names_in((root / rel).read_text(encoding="utf-8"), rel, "run_controllers", "model_facing", "live",
                 groups=False)
    for rel, p in sorted(controllers.items()):     # literals, never comments
        names_in("\n".join(_str_constants(parsed[p][1])), rel, "run_controllers", "model_facing", "live",
                 groups=False)
    # the @d4dassistant workflow: what it names and runs, and an instruction
    # file only where it loads one (#4093); the runner its `d4d api run`
    # starts is the api approach
    if workflow.is_file():
        wf_rel = _rel(root, workflow)
        s.add(wf_rel, "github_assistant", "run_shaping", "live", "the @d4dassistant workflow")
        names_in(workflow.read_text(encoding="utf-8"), wf_rel, "github_assistant", "run_shaping", "live",
                 namer_kind="code", groups=False)
    drain()
    # what an agent no live text names, and what it names in turn, is exposed:
    # available to a native run, never gating (#4054)
    for p in claude_files:
        rel = _rel(root, p)
        if p not in playbooks and rel not in referenced:
            names_in(p.read_text(encoding="utf-8"), rel, "native_agentic", "exposed", "live")
    drain()
    facts["native_referenced"] = sorted(referenced)
    facts["named_files"] = {rel: {"by": sorted(e["by"]), "runs": e["runs"], "approaches": sorted(e["approaches"])}
                            for rel, e in sorted(named.items())}
    # an assistant instruction file is a surface only where the workflow, a
    # playbook or a loaded instruction loads it (#4093)
    facts["assistant_instructions"] = {rel: sorted(loaders.get(rel, ())) for rel in sorted(assistant_set)}
    for p in claude_files:
        rel = _rel(root, p)
        if p in playbooks:
            s.add(rel, "native_agentic", "model_facing", "live", "d4d playbook (slash command)")
        elif rel in referenced:
            s.add(rel, "native_agentic", "model_facing", "live",
                  "command or agent named (path, bare name or slash command) by a playbook, live prompt, "
                  "controller or assistant instruction")
        else:
            s.add(rel, "native_agentic", "exposed", "live",
                  "handed to native runs by agentic_runtime.toolchain(); no playbook, live prompt, controller "
                  "or assistant instruction names it")

    # ---- native closure: agentic_runtime, the CLI groups the playbooks,
    # agents and instructions run, and the package modules the controllers
    # import (the native audit batch)
    for p in controllers.values():
        for node in ast.walk(parsed[p][1]):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("data_sheets_schema"):
                starts += [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                starts += [a.name for a in node.names if a.name.startswith("data_sheets_schema")]
    native_groups = sorted(g for g, by in cli_groups.get("native_agentic", {}).items() if "run_shaping" in by.values())
    starts += [f"data_sheets_schema.cli.{g}" for g in native_groups]
    facts["native_cli_groups"] = native_groups
    facts["cli_groups"] = {a: {g: {"by": sorted(by), "role": "run_shaping" if "run_shaping" in by.values()
                                   else "exposed"} for g, by in sorted(gs.items())}
                           for a, gs in sorted(cli_groups.items())}
    native_closure = _package_closure(root, sorted(set(starts)))
    facts["native_closure"] = [_rel(root, p) for p in native_closure]
    for p in native_closure:
        s.add(_rel(root, p), "native_agentic", _module_role(p), "live",
              "closure of agentic_runtime, the CLI groups the playbooks run and the controllers' imports", runs=False)
    # a CLI group run only by an exposed text, or by a controller (#4091)
    for approach, gs in sorted(cli_groups.items()):
        for g, by in sorted(gs.items()):
            if approach == "native_agentic" and g in native_groups:
                continue
            role = "run_shaping" if "run_shaping" in by.values() else "exposed"
            for p in _package_closure(root, [f"data_sheets_schema.cli.{g}"]):
                s.add(_rel(root, p), approach, role if role == "exposed" else _module_role(p), "live",
                      f"closure of the CLI group `d4d {g}` that {', '.join(sorted(by))} run", runs=False)

    # ---- deterministic arms: the commands that build a non-baseline arm's
    # bundle, and what they import (#4054)
    for p in det_closure:
        rel = _rel(root, p)
        why = (f"deterministic arm command ({arm_commands[rel]})" if rel in arm_commands
               else "import closure of the deterministic arm commands")
        s.add(rel, "deterministic", _module_role(p), "live", why, runs=False)

    # ---- interactive sessions: what Claude Code loads into a person's session
    # in a checkout, and that registered native runs switch off (#4054, #4091)
    for rel in memory:
        s.add(rel, "interactive_session", "model_facing", "live",
              "project memory Claude Code loads into an interactive session (--safe-mode and --bare skip it)")
    settings, hooks = [], []
    for rel in PROJECT_SETTINGS:
        if (root / rel).is_file():
            settings.append(rel)
            s.add(rel, "interactive_session", "run_shaping", "live",
                  "project settings an interactive session loads (its hooks run on tool use)")
            for h in _hook_scripts(root, root / rel):
                hooks.append(h)
                s.add(h, "interactive_session", "run_shaping", "live", f"hook command {rel} runs")
                if h.endswith(".py"):
                    run_scripts.setdefault(h, {})["interactive_session"] = "run_shaping"
    described = []
    for base, pattern in SESSION_DESCRIBED:
        if (root / base).is_dir():
            described += [p for p in sorted((root / base).glob(pattern)) if p.is_file()]
    for p in described:
        rel = _rel(root, p)
        s.add(rel, "interactive_session", "exposed", "live",
              "Claude Code lists its description in every interactive session (the agent types of the Agent "
              "tool, the commands and skills); its body loads only when it is invoked")
        s.files[rel].loaded["interactive_session"] = session_description_lines(p.read_text(encoding="utf-8"))
    skills = sorted(_rel(root, p) for p in (root / ".claude/skills").glob("*/SKILL.md"))
    described_set = {_rel(root, p) for p in described}
    launches = launch_flags(controllers, parsed)
    # not shown to pass --safe-mode: the session descriptions stay on; not
    # shown to pass --safe-mode or --bare: the memory and the hooks too (#4131)
    unsafe = [x["site"] for x in launches if not x["carries"]]
    memory_on = [x["site"] for x in launches if not x["memory_off"]]
    facts["interactive"] = {
        "memory": memory, "memory_named_by": sorted(memory_named_by), "settings": settings,
        "hooks": sorted(set(hooks)), "skills": skills, "described": sorted(described_set),
        "launches": launches, "native_launch_sites": [x["site"] for x in launches],
        "customizations_off": sorted({e for x in launches if x["carries"] for e in x["evidence"]}),
        "launches_without_customizations_off": unsafe,
        "memory_off": sorted({e for x in launches if x["memory_off"] for e in x["memory_evidence"]}),
        "launches_without_memory_off": memory_on}

    # ---- what the scripts a text or a hook runs import (#4091): `python
    # x.py` puts x's directory on sys.path (`-m` a package module does not);
    # the CLI package is not entered, its groups are followed where run
    opaque = frozenset(_resolved(root / r) for r in CLI_PACKAGE)
    script_imports: dict[str, list[str]] = {}
    for rel, by in sorted(run_scripts.items()):
        if not (root / rel).is_file():
            continue
        dirs = [] if _package_module(rel) else [Path(rel).parent.as_posix()]
        members, _ = _code_closure(root, [root / rel], stop, dirs=dirs, opaque=opaque)
        for q in members:
            qrel = _rel(root, q)
            if qrel == rel or not _is_inside(q, root):
                continue
            script_imports.setdefault(rel, []).append(qrel)
            for approach, role in sorted(by.items()):
                s.add(qrel, approach, role if role == "exposed" else _module_role(q), "live",
                      f"imported by {rel}, which is run in {approach}", runs=False)
    facts["run_script_imports"] = {k: sorted(v) for k, v in sorted(script_imports.items())}

    # a registered launch not shown to switch them off may load what an
    # interactive session loads (#4092, #4156): those surfaces, and what the
    # hooks import, are its too. A launch with `--bare` alone skips the
    # memory and the hooks but still lists the commands, agents and skills
    # (#4131).
    if unsafe:
        for rel, surf in sorted(s.files.items()):
            role = surf.roles.get("interactive_session")
            if role is None:
                continue
            loaders = unsafe if rel in described_set else memory_on
            if not loaders:
                continue
            s.add(rel, "run_controllers", role, "live", "may be loaded by a registered native launch not shown to "
                  "switch it off (" + ", ".join(loaders) + ")",
                  runs="interactive_session" in surf.runs, raw="interactive_session" in surf.raw)
            if "interactive_session" in surf.loaded:
                surf.loaded["run_controllers"] = list(surf.loaded["interactive_session"])

    # ---- every module that calls a model client (#4023), wherever it is
    in_closure = (set(facts["api_closure"]) | set(facts["native_closure"]) | set(facts["deterministic_closure"])
                  | set(controllers))
    evaluation = evaluation_controllers(root, parsed, index, controllers, evaluation_reached)
    model_clients = {}
    for p, (text, tree) in sorted(parsed.items()):
        rel = _rel(root, p)
        why = model_client_evidence(tree)
        if not why:
            continue
        if rel in controllers:
            where = "run_controllers"
        elif rel in in_closure:
            where = "the api/native/deterministic import closure"
        elif rel.startswith("notes/"):
            where = "other_model_client"
            s.add(rel, "other_model_client", "run_shaping", "live",
                  "calls a model client outside the generation controllers (a diagnostic probe, a transport "
                  "or an evaluator): " + ", ".join(why))
        elif GENERATOR_TEXT.search(text) and not EVALUATION_PATH.search(rel):
            where = "legacy_monolithic"
            s.add(rel, "legacy_monolithic", "run_shaping", "legacy",
                  "calls a model client to write a D4D record outside the runner: " + ", ".join(why))
        else:
            where = "other_model_client"
            s.add(rel, "other_model_client", "run_shaping", "live",
                  "calls a model client and is an evaluator or names no D4D record: " + ", ".join(why))
        model_clients[rel] = {"evidence": why, "classified": where}
    facts["model_clients"] = model_clients
    for rel, why in evaluation.items():
        s.add(rel, "other_model_client", "run_shaping", "live", why)
    facts["evaluation_controllers"] = evaluation

    # ---- github assistant: the workflow and what it names were found above;
    # the condition its `d4d api run` runs
    if gh:
        s.add(cond["prompts"][gh["condition_name"]], "github_assistant", "model_facing", "live",
              f"condition the workflow runs ({gh['condition_basis']})")

    # ---- shared schema
    schema_dir = src / "schema"
    roots = ("data_sheets_schema.yaml", "data_sheets_schema_core.yaml")
    closure = sorted({p for r in roots for p in _schema_closure(schema_dir, r)})
    facts["schema_closure"] = [_rel(root, p) for p in closure]
    for p in closure:
        s.add(_rel(root, p), "shared_schema", "model_facing", "live", "generation schema import closure")
    for rel in toolchain["schemas"]:
        s.add(rel, "shared_schema", "model_facing", "live", "schema file agentic_runtime.toolchain() hands a "
              "native run, read whole", raw=True)
    # hand-kept: why each of these reaches a model is not in an import graph
    for rel, role, why in (
            ("src/data_sheets_schema/profiles.py", "run_shaping", "profile selection"),
            ("src/data_sheets_schema/registry.py", "run_shaping", "manifest as project registry"),
            ("src/data_sheets_schema/b2ai_registry_vocabularies.yaml", "model_facing",
             "vocabulary pin rendered into the digest under the bridge2ai profile"),
            ("data/preprocessed/source_manifest.yaml", "model_facing",
             "study manifest: ranking, naming and scope blocks are rendered from it")):
        if (root / rel).exists():
            s.add(rel, "shared_schema", role, "live", why)

    # ---- legacy monolithic: the generators that call a client were found
    # above from the call; these are the pre-runner helpers that write or load
    # prompts without calling a client themselves (a name glob: what makes a
    # helper part of a manual prompt workflow is not in its imports)
    for p in sorted((root / "src/download").glob("process_*.py")) + \
            [p for p in sorted((root / "src/download").glob("*.py")) if re.search(r"d4d|prompt_loader", p.name)]:
        if _rel(root, p) not in s.files:
            s.add(_rel(root, p), "legacy_monolithic", "run_shaping", "legacy", "legacy generation helper script")
    facts["legacy_scripts"] = sorted(r for r, f in s.files.items()
                                     if "legacy_monolithic" in f.approaches and r.endswith(".py"))
    for p in sorted(prompts_dir.glob("d4d_concatenated_*.txt")):
        s.add(_rel(root, p), "legacy_monolithic", "model_facing", "legacy", "legacy monolithic prompt")
    # every prompt set beside the conditions, other than the tuned components
    components = (root / cond["components"]).resolve() if cond["components"] else None
    prompt_sets = [d for d in sorted(prompts_dir.iterdir()) if d.is_dir() and not d.name.startswith((".", "_"))
                   and d.resolve() != components]
    facts["legacy_prompt_sets"] = [d.name for d in prompt_sets]
    for d in prompt_sets:
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix in TEXT_SUFFIXES:
                if p.name.lower() == "readme.md":
                    s.add(_rel(root, p), "legacy_monolithic", "run_shaping", "legacy", "prompt-set README")
                else:
                    s.add(_rel(root, p), "legacy_monolithic", "model_facing", "legacy",
                          f"legacy prompt set ({d.name})")

    # ---- upstream input (listed, never gates)
    for rel, why in shared.items():
        s.add(rel, "shared_input", "run_shaping", "live", "input acquisition / bundle shaping: " + why)

    # ---- text a model receives, by data flow (#4054)
    spans = model_text_spans(root, parsed, index, controllers)
    for rel, sp in spans.items():
        if rel in s.files:
            s.files[rel].text_spans = sp
    # reported where it changes something: a module no approach already
    # treats as model-facing as a whole
    facts["model_text"] = {rel: list(dict.fromkeys(label for *_, label in sp)) for rel, sp in sorted(spans.items())
                           if rel in s.files and "model_facing" not in s.files[rel].roles.values()}
    return s, facts


# --------------------------------------------------------------------------
# exceptions


EXCEPTION_KEYS = {"path", "token", "category", "context", "reason", "decision"}


def _str_or_list(value, where: str) -> list[str]:
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
        raise ConfigError(f"{where} must be a string or a list of strings, got {value!r}")
    return list(values)


def load_exceptions(path: Path = EXCEPTIONS_FILE) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise ConfigError(f"{path}: the top level must be a mapping with an `exceptions:` list")
    entries = doc.get("exceptions") or []
    if not isinstance(entries, list):
        raise ConfigError(f"{path}: `exceptions` must be a list")
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ConfigError(f"exception {i}: an entry must be a mapping")
        extra = set(e) - EXCEPTION_KEYS
        if extra:
            raise ConfigError(f"exception {i}: unknown keys {sorted(extra)}")
        for key in ("path", "reason", "decision"):
            if not e.get(key):
                raise ConfigError(f"exception {i}: `{key}` is required")
        if not e.get("token") and not e.get("category"):
            raise ConfigError(f"exception {i}: name a `token` or a `category`")
        cats = _str_or_list(e["category"], f"exception {i} category") if e.get("category") else []
        bad = set(cats) - set(CATEGORIES)
        if bad:
            raise ConfigError(f"exception {i}: unknown category {sorted(bad)}")
        e["_categories"] = cats
        e["_paths"] = _str_or_list(e["path"], f"exception {i} path")
        e["_contexts"] = _str_or_list(e["context"], f"exception {i} context") if e.get("context") else []
        e["_token"] = _compile(e["token"], f"exception {i} token") if e.get("token") else None
        e["_index"] = i
    return entries


def exception_for(hit: dict, exceptions: list[dict]) -> dict | None:
    for e in exceptions:
        if not any(fnmatch.fnmatchcase(hit["path"], g) for g in e["_paths"]):
            continue
        if e["_categories"] and hit["category"] not in e["_categories"]:
            continue
        if e["_token"] is not None and not e["_token"].fullmatch(hit["match"]):
            continue
        if e["_contexts"] and hit["context"] not in e["_contexts"]:
            continue
        return e
    return None


# --------------------------------------------------------------------------
# scanning


def _model_text_ranges(tree) -> list[tuple[int, int, str]]:
    if tree is None:
        return []
    return [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and MODEL_TEXT_FUNCTION.match(n.name)]


def scan_file(root: Path, surface: Surface, tokens: list[Token]) -> list[dict]:
    """Every token hit in one surface. A file that cannot be read, or a
    Python file that does not parse (#4092), raises: the caller decides, and
    `run` refuses to report on a surface it could not see. Each approach that
    reaches the file judges a hit by the file's role in that approach
    (#4054): text counts where the role is model-facing, where run-shaping
    code renders model text (a function named for it in a run controller, or
    text found by data flow), and on the lines the approach loads whatever
    the role (a description a session lists, #4091); a YAML comment counts
    where the model reads the file raw (#4091); code counts unless the role
    is exposed, and in a YAML, config or shell file that no approach hands
    to a model a branch, default or per-project key is code (#4091); and
    nothing in a `__main__` block counts for an approach that only imports
    the module."""
    path = root / surface.path
    text = path.read_text(encoding="utf-8")
    is_py = path.suffix == ".py"
    tree = None
    if is_py:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError) as exc:
            raise UnparsedSurface(surface.path, exc) from exc
    roles = surface.roles or {a: surface.role for a in surface.approaches}
    # In a run controller, the string literals of a function that renders
    # what a model receives (render_instruction, render_system, ...) are
    # model-facing text even though the module as a whole shapes the run;
    # data flow found the rest at discovery (#4054).
    spans = list(surface.text_spans) if is_py else []
    if is_py and roles.get("run_controllers") == "run_shaping":
        spans += _model_text_ranges(tree)
    main = _main_block_lines(tree) if is_py and any(a not in surface.runs for a in roles) else []
    code_units = not is_py and "model_facing" not in roles.values() and "run_shaping" in roles.values()
    raw_comments = path.suffix.lower() in YAML_SUFFIXES
    hits = []
    for line, context, unit, src in units_for(path, surface.path, text, tree, code=code_units):
        label = next((name for a, b, name in spans if a <= line <= b), None) \
            if context == "string_literal" else None
        in_main = any(a <= line <= b for a, b in main)
        reaches: dict[str, tuple[bool, bool]] = {}
        loaded: dict[str, str] = {}
        raw = False
        for a, r in roles.items():
            here = next((name for lo, hi, name in surface.loaded.get(a, ()) if lo <= line <= hi), None)
            if (r == "exposed" and here is None) or (in_main and a not in surface.runs):
                reaches[a] = (False, False)
                continue
            text_counts = context in MODEL_FACING_CONTEXTS and (r == "model_facing" or label is not None
                                                                or here is not None)
            if context == "comment" and raw_comments and r == "model_facing" and a in surface.raw:
                text_counts = raw = True
            reaches[a] = (text_counts, context in CODE_CONTEXTS and r != "exposed")
            if here is not None and text_counts:
                loaded[a] = here
        model_facing = any(t for t, _ in reaches.values())
        code = any(c for _, c in reaches.values())
        gates_in = sorted(a for a, (t, c) in reaches.items() if (t or c) and APPROACHES[a][0])
        for _, _, tok, matched in match_text(unit, tokens):
            hit = {
                "path": surface.path, "line": line, "approaches": list(surface.approaches),
                "role": surface.role, "status": surface.status, "context": context,
                "category": tok.category, "match": matched, "pattern": tok.pattern,
                "model_facing": model_facing, "code": code, "gates_in": gates_in,
                "snippet": src.strip()[:180],
            }
            if label is not None:
                hit["model_text_function"] = label
            if in_main:
                hit["main_block"] = True
            if loaded:
                hit["loaded_in"] = loaded
            if raw:
                hit["read_raw"] = True
            hits.append(hit)
    return hits


GENERATION_NAMES = re.compile(r"\b(build_phase|resolve_prompt|RunSpec|digest_text|render_prompt|"
                              r"playbook_text|prompt_body|phase_instruction)\b")


def scan_tests(root: Path, tokens: list[Token]) -> tuple[list[dict], list[str]]:
    """gc_project literals asserted on by a test that exercises generation,
    and the tests of this audit, which are not listed: they plant tokens to
    check the scanner, which is not generation behaviour (#4056)."""
    out, own = [], []
    gc = [t for t in tokens if t.category == "gc_project"]
    for p in sorted((root / "tests").rglob("test_*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not GENERATION_NAMES.search(text):
            continue
        if SKILL_DIR.name in text:
            own.append(_rel(root, p))
            continue
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError) as exc:     # never skipped in silence (#4092)
            raise _unparsed([f"{_rel(root, p)} ({type(exc).__name__}: {exc})"]) from exc
        lines = text.splitlines()
        asserted = set()
        for node in ast.walk(tree):
            is_assert = isinstance(node, ast.Assert) or (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr.startswith("assert") and node.func.attr not in
                {"assertRaises", "assertRaisesRegex"})
            if is_assert:
                asserted.update(id(n) for n in ast.walk(node) if isinstance(n, ast.Constant))
        for node in ast.walk(tree):
            if id(node) in asserted and isinstance(node, ast.Constant) and isinstance(node.value, str):
                for _, _, tok, matched in match_text(node.value, gc):
                    out.append({"path": _rel(root, p), "line": node.lineno, "category": tok.category,
                                "match": matched, "context": "test_assertion",
                                "snippet": lines[node.lineno - 1].strip()[:180]})
    return out, own


def is_violation(hit: dict) -> bool:
    """A gc_project hit with no exception that some gating approach counts:
    model-facing text or a code branch/table there (`gates_in`)."""
    return hit["category"] == "gc_project" and hit.get("exception") is None and bool(hit.get("gates_in"))


# --------------------------------------------------------------------------
# self-test: a scanner that sees nothing cannot pass


#: What the self-test plants. Every planted item is checked for its context
#: (Python) or category (Markdown) AND the line it was planted on (#4026):
#: an implicitly concatenated literal whose token sits on its second line, a
#: triple-quoted block, the table forms #4024 added (a frozenset constant, a
#: lookup default, a keyword argument, a loop tuple) and the ones #4130 added
#: (an `or` default, a value wrapped in a call, a regex test).
SELF_TEST_SEEDS = {
    "seed.md": ("# Seed\n\nRecord the AI-READI release.\nThe Bridge2AI program funds it.\n"
                "Describe the clinical cohort.\n"),
    "seed.py": ("def f(project):\n"                              # 1
                "    if project == 'CHORUS':\n"                  # 2
                "        return 'see fairhub'\n"                 # 3
                "    # a VOICE comment\n"                        # 4
                "    return {'CM4AI': 1}\n"                      # 5
                "TEXT = ('first line '\n"                        # 6
                "        'second physionet line')\n"             # 7
                "SPECIAL = frozenset({'AI_READI'})\n"            # 8
                "def g(d, p):\n"                                 # 9
                "    return d.get(p, 'VOICE_PEDIATRIC')\n"       # 10
                "NOTE = '''\n"                                   # 11
                "first\n"                                        # 12
                "see the voicepeds page\n"                       # 13
                "'''\n"                                          # 14
                "run(project='aireadi')\n"                       # 15
                "for name in ('dataverse',):\n"                  # 16
                "    pass\n"                                     # 17
                "DEFAULT = name or 'healthdatanexus'\n"          # 18
                "RAW = Path('data/raw/b2ai-voice')\n"            # 19
                "MATCHED = re.fullmatch('cm4ai', name)\n"),      # 20
}
SELF_TEST_EXPECT = {
    "seed.md": {("gc_project", "AI-READI", 3), ("bridge2ai_program", "Bridge2AI", 4),
                ("biomedical_clinical", "clinical", 5)},
    "seed.py": {("code_branch", "CHORUS", 2), ("string_literal", "fairhub", 3), ("comment", "VOICE", 4),
                ("code_table", "CM4AI", 5), ("string_literal", "physionet", 7),
                ("code_table", "AI_READI", 8), ("code_table", "VOICE_PEDIATRIC", 10),
                ("string_literal", "voicepeds", 13), ("code_table", "aireadi", 15),
                ("code_table", "dataverse", 16), ("code_table", "healthdatanexus", 18),
                ("code_table", "b2ai-voice", 19), ("code_branch", "cm4ai", 20)},
}


def self_test(tokens: list[Token]) -> dict:
    with tempfile.TemporaryDirectory(prefix="d4d-specificity-selftest-") as d:
        root = Path(d)
        found = {}
        for name, text in SELF_TEST_SEEDS.items():
            (root / name).write_text(text, encoding="utf-8")
            surf = Surface(name, ["api"], "model_facing", "live", "self-test")
            found[name] = scan_file(root, surf, tokens)
    problems = []
    md = {(h["category"], h["match"], h["line"]) for h in found["seed.md"]}
    py = {(h["context"], h["match"], h["line"]) for h in found["seed.py"]}
    for want in sorted(SELF_TEST_EXPECT["seed.md"] - md):
        problems.append(f"markdown: planted {want} not found as (category, token, line) in {sorted(md)}")
    for want in sorted(SELF_TEST_EXPECT["seed.py"] - py):
        problems.append(f"python: planted {want} not found as (context, token, line) in {sorted(py)}")
    viol = [h for h in found["seed.py"] if is_violation({**h, "exception": None})]
    if not viol:
        problems.append("a planted gc_project branch was not a violation")
    counts = {c: sum(t.category == c for t in tokens) for c in CATEGORIES}
    imported = sum(t.source.startswith(NEUTRALITY_TEST) for t in tokens)
    if imported == 0:
        problems.append("no token was imported from the neutrality test")
    return {"passed": not problems, "problems": problems, "token_counts": counts,
            "imported_from_neutrality_test": imported}


# --------------------------------------------------------------------------
# "api" meaning, derived from the code (#4022, #4025, #4055, #4057, #4058)


def _function(tree: ast.Module, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def shape_of(model_phases: list, followups: list, full_schema: bool) -> str:
    """MONOLITHIC only for one model phase, no follow-up turn, and the full
    LinkML schema sent (#4057): one call that sends a schema digest is not
    the owner's monolithic approach."""
    if len(model_phases) > 1 or followups:
        return "MULTI-PHASE"
    return "MONOLITHIC" if full_schema else "SINGLE-CALL (schema digest, not monolithic)"


def _int_values(node) -> list[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _int_values(node.body) + _int_values(node.orelse)
    return []


def _int_set(node) -> list[int] | None:
    """The ints a literal collection or a literal range() spells, else None."""
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        vals = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, int)
                and not isinstance(e.value, bool)]
        return vals if len(vals) == len(node.elts) else None
    if isinstance(node, ast.Call) and _attr_or_name(node.func) == "range" and 0 < len(node.args) <= 3 and \
            all(isinstance(a, ast.Constant) and isinstance(a.value, int) for a in node.args):
        return list(range(*[a.value for a in node.args]))
    return None


def _compares(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            yield n.left, n.ops[0], n.comparators[0]


def _attr_or_name(node) -> str | None:
    return node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) else None


def derive_agentic_audit_from(build: ast.AST) -> int:
    """The renderer from which `build_phase` refuses the audit phase: an `if`
    whose test compares `render_version >= N` and `phase == "audit"` (either
    order, either side) and whose body raises. Not found, or two different
    floors, is not derived, never None (#4025)."""
    found = set()
    for node in ast.walk(build):
        # a guard: the raise is the branch itself, not one nested deeper
        if not isinstance(node, ast.If) or not any(isinstance(b, ast.Raise) for b in node.body):
            continue
        floors, audit = [], False
        for left, op, right in _compares(node.test):
            if _attr_or_name(left) == "render_version" and isinstance(op, ast.GtE):
                floors += _int_values(right)
            if _attr_or_name(right) == "render_version" and isinstance(op, ast.LtE):
                floors += _int_values(left)
            sides = {_attr_or_name(left), getattr(right, "value", None), _attr_or_name(right),
                     getattr(left, "value", None)}
            if isinstance(op, ast.Eq) and "phase" in sides and "audit" in sides:
                audit = True
        if floors and audit:
            found.update(floors)
    if len(found) != 1:
        raise _not_derived("the renderer from which the audit phase is agentic",
                           f"build_phase has {sorted(found) or 'no'} raising `render_version >= N and "
                           "phase == 'audit'` guard")
    return found.pop()


def derive_default_renderer(tree: ast.Module) -> dict:
    """RunSpec's renderer when none is given: `self.render_version = A if
    self.is_agentic else B` (or the negated test). Not found is not derived."""
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and _attr_or_name(node.targets[0]) == "render_version" and isinstance(node.value, ast.IfExp)):
            continue
        test, body, orelse = node.value.test, node.value.body, node.value.orelse
        negated = isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
        if negated:
            test = test.operand
        if _attr_or_name(test) != "is_agentic" or not (_int_values(body) and _int_values(orelse)):
            continue
        agentic, api = (orelse, body) if negated else (body, orelse)
        return {"agentic": _int_values(agentic)[0], "api": _int_values(api)[0]}
    raise _not_derived("the default renderer", "no `render_version = A if is_agentic else B` in api_runner.py")


def derive_admitted_renderers(tree: ast.Module) -> list[int]:
    """The renderers RunSpec admits: its `render_version not in (...)` refusal."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and any(isinstance(b, ast.Raise) for b in node.body):
            for left, op, right in _compares(node.test):
                if _attr_or_name(left) == "render_version" and isinstance(op, ast.NotIn) and _int_set(right):
                    return sorted(_int_set(right))
    raise _not_derived("the renderers RunSpec admits", "no raising `render_version not in (...)` in api_runner.py")


def derive_execute_refusal(tree: ast.Module, admitted: list[int]) -> dict:
    """The renderers `api_runner.execute` refuses before it runs anything: a
    raising `render_version in (...)` or `>= N` test in its body (#4055). No
    such test is an empty refusal, reported as such."""
    fn = _function(tree, "execute")
    if fn is None:
        raise _not_derived("what api_runner.execute refuses", "api_runner.py defines no execute()")
    refused, line = set(), None
    for node in ast.walk(fn):
        if not (isinstance(node, ast.If) and any(isinstance(b, ast.Raise) for b in node.body)):
            continue
        for left, op, right in _compares(node.test):
            if _attr_or_name(left) != "render_version":
                continue
            if isinstance(op, ast.In) and _int_set(right):
                refused |= set(_int_set(right))
                line = line or node.lineno
            elif isinstance(op, ast.GtE) and _int_values(right):
                refused |= {r for r in admitted if r >= _int_values(right)[0]}
                line = line or node.lineno
    return {"refused": sorted(refused), "line": line}


def _renderer_options(tree: ast.Module) -> dict[str, dict]:
    """dest -> {flag, choices, default, line} for each argparse or click
    option whose destination names a renderer (#4055)."""
    out = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _attr_or_name(node.func) in {"add_argument", "option", "argument"}):
            continue
        flags = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        dest_node = kw.get("dest")
        dest = dest_node.value if isinstance(dest_node, ast.Constant) else \
            next((f.lstrip("-").replace("-", "_") for f in flags if f.startswith("--")), None)
        if not dest or "render" not in dest:
            continue
        default = _int_values(kw["default"]) if "default" in kw else []
        out[dest] = {"flag": next((f for f in flags if f.startswith("--")), dest),
                     "choices": _int_set(kw["choices"]) if "choices" in kw else None,
                     "default": default[0] if default else None, "line": node.lineno}
    return out


def _renderer_value(node, fn, consts: dict, options: dict, seen=frozenset()) -> tuple[list[int] | None, str]:
    """(renderers an expression can hold, where they come from) (#4055).
    None is unbounded or unresolved: a free option, arithmetic, a call. An
    empty list is a value inherited from a record, a registration, a spec or
    a caller: set where that was written, by a setter found there."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return [node.value], "literal"
        return None, f"unresolved: {node.value!r}"
    if isinstance(node, ast.IfExp):
        a, oa = _renderer_value(node.body, fn, consts, options, seen)
        b, ob = _renderer_value(node.orelse, fn, consts, options, seen)
        return (None if a is None or b is None else sorted(set(a) | set(b))), " or ".join(dict.fromkeys([oa, ob]))
    if isinstance(node, ast.Name):
        local = _local_assignments(fn) if fn is not None else {}
        if node.id in local and node.id not in seen:
            values, origins = [], []
            for v in local[node.id]:
                r, o = _renderer_value(v, fn, consts, options, seen | {node.id})
                if r is None:
                    return None, o
                values += r
                origins.append(o)
            return sorted(set(values)), " or ".join(dict.fromkeys(origins))
        if fn is not None and node.id in _params(fn):
            return [], f"inherited (the caller's {node.id})"
        value = consts.get(node.id)
        if isinstance(value, int) and not isinstance(value, bool):
            return [value], f"constant {node.id}"
        return None, f"unresolved: {node.id}"
    if isinstance(node, ast.Attribute) and node.attr == "render_version" or (
            isinstance(node, ast.Attribute) and node.attr in options):
        if isinstance(node.value, ast.Name) and node.value.id in ARGS_NAMES and node.attr in options:
            opt = options[node.attr]
            if opt["choices"] is not None:
                return sorted(opt["choices"]), f"option {opt['flag']} (choices, line {opt['line']})"
            return None, f"option {opt['flag']} (no choices, default {opt['default']}, line {opt['line']})"
        if isinstance(node.value, ast.Name) and node.value.id in ARGS_NAMES:
            return None, f"unresolved: {ast.unparse(node)} (no such option in the module)"
        return [], f"inherited ({ast.unparse(node)[:60]})"
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == "render_version":
        return [], f"inherited ({ast.unparse(node)[:60]})"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and \
            node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "render_version":
        if len(node.args) > 1:
            d, od = _renderer_value(node.args[1], fn, consts, options, seen)
            return d, f"inherited ({ast.unparse(node.func.value)[:40]}), else {od}"
        return [], f"inherited ({ast.unparse(node.func.value)[:40]})"
    return None, f"unresolved: {ast.unparse(node)[:60]}"


def _str_value(node, fn, consts: dict) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        local = _local_assignments(fn) if fn is not None else {}
        values = {_str_value(v, None, consts) for v in local.get(node.id, [])}
        if len(values) == 1 and None not in values:
            return values.pop()
        if node.id not in local and isinstance(consts.get(node.id), str):
            return consts[node.id]
    return None


def _runtimes(tree: ast.Module, consts: dict) -> tuple[list, dict]:
    """Every runtime a module names for a spec or a job (`runtime=` keywords,
    `"runtime":` entries), resolved where it can be; and per container."""
    found, per = [], {}
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, ast.Call):
            pairs = [k.value for k in node.keywords if k.arg == "runtime"]
        elif isinstance(node, ast.Dict):
            pairs = [v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and k.value == "runtime"]
        for v in pairs:
            value = _str_value(v, _innermost_function(tree, v.lineno), consts)
            found.append(value)
            per[id(node)] = value
    return found, per


def _renderer_setters(tree: ast.Module, floor: int, consts: dict, options: dict,
                      agentic: list[str]) -> tuple[list[dict], int]:
    """Where a module sets a renderer, in any spelling (#4055): a
    `render_version=` keyword, a `["render_version"] =` or `.render_version
    =` assignment, or a `"render_version":` entry, whatever the value is: a
    literal, a constant, an option, an expression. A value inherited from a
    record, a registration or a spec propagates a renderer set elsewhere and
    is counted, not listed. Each listed setter says whether it can reach the
    floor (an unresolved value can) and which runtime its spec names: its
    own call or dict, else every runtime the module names when all of them
    are agentic."""
    found, per = _runtimes(tree, consts)
    module_runtime = " / ".join(sorted(set(found))) if found and all(r in agentic for r in found) else None
    setters, propagating = [], 0
    for node in ast.walk(tree):
        sites = []
        if isinstance(node, ast.Call):
            sites = [(k.value, node) for k in node.keywords if k.arg == "render_version"]
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                key = t.slice.value if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) \
                    else t.attr if isinstance(t, ast.Attribute) else None
                if key == "render_version":
                    sites.append((node.value, None))
        elif isinstance(node, ast.Dict):
            sites = [(v, node) for k, v in zip(node.keys, node.values)
                     if isinstance(k, ast.Constant) and k.value == "render_version"]
        for value, container in sites:
            fn = _innermost_function(tree, value.lineno)
            renderers, origin = _renderer_value(value, fn, consts, options)
            if renderers == []:
                propagating += 1
                continue
            runtime = per.get(id(container)) if container is not None else None
            setters.append({"line": value.lineno, "renderers": renderers, "origin": origin,
                            "reaches_floor": renderers is None or max(renderers) >= floor,
                            "runtime": runtime or module_runtime})
    return setters, propagating


def _refuses_non_agentic(test) -> bool:
    """A test that is true for every parent that is not an agentic run:
    `not X.is_agentic`, `X.runtime not in AGENTIC_RUNTIMES`, or an `or`
    with one of them as a disjunct (#4057). `X.is_agentic` refuses the
    agentic parents instead, and `a and not X.is_agentic` refuses a
    non-agentic parent only when `a` holds."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) and _attr_or_name(test.operand) == "is_agentic":
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.NotIn) and \
            _attr_or_name(test.left) == "runtime" and (_attr_or_name(test.comparators[0]) or "").endswith(
                "AGENTIC_RUNTIMES"):
        return True
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        return any(_refuses_non_agentic(v) for v in test.values)
    return False


def _agentic_parent_gates(tree: ast.Module) -> list[dict]:
    """`if (spec.condition != "X" or spec.render_version != N or not
    spec.is_agentic ...): raise`: a continuation that refuses any parent
    that is not an agentic run (of condition X at renderer N, when named)."""
    gates = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and any(isinstance(b, ast.Raise) for b in node.body)):
            continue
        if not _refuses_non_agentic(node.test):
            continue
        gate = {"line": node.lineno, "condition": None, "parent_renderer": None}
        disjuncts = node.test.values if isinstance(node.test, ast.BoolOp) else [node.test]
        for d in disjuncts:
            for left, op, right in _compares(d):
                if isinstance(op, ast.NotEq) and _attr_or_name(left) == "condition" and isinstance(right, ast.Constant):
                    gate["condition"] = right.value
                if isinstance(op, ast.NotEq) and _attr_or_name(left) == "render_version":
                    vals = _int_values(right)
                    gate["parent_renderer"] = vals[0] if vals else None
        gates.append(gate)
    return gates


def _renderer_inputs(tree: ast.Module) -> list[str]:
    """Where `d4d api` could hand RunSpec a renderer: a `render_version=`
    keyword, a "render_version" key (kw["render_version"], a dict entry), or
    a click/argparse option whose flag names a renderer."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "render_version":
            out.append(f"line {node.value.lineno}: render_version= keyword")
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and \
                node.slice.value == "render_version":
            out.append(f"line {node.lineno}: [\"render_version\"]")
        elif isinstance(node, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == "render_version"
                                                for k in node.keys):
            out.append(f"line {node.lineno}: \"render_version\" entry")
        elif isinstance(node, ast.Call) and _attr_or_name(node.func) in {"option", "argument", "add_argument"} and \
                any(isinstance(a, ast.Constant) and isinstance(a.value, str) and "render" in a.value
                    for a in node.args):
            out.append(f"line {node.lineno}: a renderer option")
    return out


def _span(values: list[int] | None) -> str:
    if values is None:
        return "any admitted"
    if len(values) > 2 and values == list(range(values[0], values[-1] + 1)):
        return f"{values[0]}-{values[-1]}"
    return ", ".join(map(str, values))


def audit_continuations(root: Path, floor: int, controllers: list[str], runner_tree: ast.Module,
                        agentic: list[str]) -> dict:
    """Whether a native agent can do part of an API run (#4022, #4055).

    - A native continuation is a run controller that rebuilds a parent run's
      spec (`RunSpec.from_render_spec`) to run a phase of it natively, at any
      renderer: the audit continuation registers renderers 14-23, the
      finalization one inherits its renderer. Its controller package
      (directory) must hold a gate that refuses any parent that is not an
      agentic run; one without could continue an API run.
    - Every renderer setter in a controller, in any spelling, is resolved
      (literal, constant, option, expression). One that can reach the floor
      (from which `build_phase` refuses the audit and it becomes a registered
      native batch) is covered when its package holds such a gate, or when
      its spec names an agentic runtime (a native run from its start). A
      setter that can reach the floor with neither, or whose value cannot be
      resolved, makes a runtime hybrid possible: never a false "no".
    - An API run that itself reaches the floor is not a hybrid: `build_phase`
      refuses its audit, and `api_runner.execute` refuses what it lists."""
    setters, propagating, packages, gates_by_dir = [], 0, {}, {}
    for rel in controllers:
        p = root / rel
        text, tree = _parse(p)
        if tree is None:
            continue
        consts = _module_constants(p)
        if "render_version" in text:
            found, prop = _renderer_setters(tree, floor, consts, _renderer_options(tree), agentic)
            setters += [{"path": rel, **x} for x in found]
            propagating += prop
        sites = sorted({n.lineno for n in ast.walk(tree)
                        if isinstance(n, ast.Call) and _attr_or_name(n.func) == "from_render_spec"})
        if sites:
            packages.setdefault(_resolved(p).parent, []).extend(f"{rel}:{line}" for line in sites)
        for g in _agentic_parent_gates(tree):
            gates_by_dir.setdefault(_resolved(p).parent, []).append({"path": rel, **g})
    used: dict[str, dict] = {}

    def gates_at(d) -> list[str]:
        gs = gates_by_dir.get(d, [])
        used.update({f"{g['path']}:{g['line']}": g for g in gs})
        return sorted(f"{g['path']}:{g['line']}" for g in gs)

    continuations = [{"package": _rel(root, d), "sites": sorted(set(sites)), "gates": gates_at(d)}
                     for d, sites in sorted(packages.items())]
    for x in setters:
        x["gates"] = gates_at(_resolved(root / x["path"]).parent) if x["reaches_floor"] else []
        x["covered"] = ("below the floor" if not x["reaches_floor"] else
                        "gated continuation package" if x["gates"] else
                        f"agentic runtime ({x['runtime']})" if x["runtime"] and all(
                            r in agentic for r in x["runtime"].split(" / ")) else None)
    ungated = [c for c in continuations if not c["gates"]]
    uncovered = [x for x in setters if x["covered"] is None]
    admitted = derive_admitted_renderers(runner_tree)
    refusal = derive_execute_refusal(runner_tree, admitted)
    cli_inputs = _renderer_inputs(_tree(root / CLI_API))
    defaults = derive_default_renderer(runner_tree)

    def where(x):
        return f"{x['path']}:{x['line']}"

    gate_text = "; ".join(f"{k} refuses a parent that is not an agentic run"
                          + (f" of {g['condition']}" if g["condition"] else "")
                          + (f" at renderer {g['parent_renderer']}" if g["parent_renderer"] is not None else "")
                          for k, g in sorted(used.items()))
    reach = [x for x in setters if x["reaches_floor"]]
    gated = [x for x in reach if x["covered"] == "gated continuation package"]
    native = [x for x in reach if x["covered"] and x["covered"].startswith("agentic")]
    parts = []
    if gated:
        parts.append("native continuations (" + ", ".join(f"{where(x)}: {_span(x['renderers'])}" for x in gated)
                     + ")")
    if native:
        parts.append("agentic generations, native from their start (" + ", ".join(
            f"{where(x)}: {_span(x['renderers'])}, {x['origin']}, runtime {x['runtime']}" for x in native) + ")")
    reasons = []
    if ungated:
        reasons.append("native continuations with no agentic-parent gate in their package: "
                       + "; ".join(f"{c['package']} ({', '.join(c['sites'])})" for c in ungated))
    if uncovered:
        reasons.append(f"renderer >= {floor} can be set with neither an agentic-parent gate nor an agentic "
                       "runtime: " + "; ".join(f"{where(x)} ({x['origin']})" for x in uncovered))
    if reasons:
        why = "; ".join(reasons)
    elif reach:
        why = f"renderer >= {floor} is set by " + " and by ".join(parts)
    else:
        why = f"no controller sets renderer >= {floor}"
    cont_text = ("every native continuation of a parent run, at any renderer ("
                 + "; ".join(f"{c['package']}: {len(c['sites'])} spec rebuild" + ("s" if len(c["sites"]) != 1 else "")
                             for c in continuations)
                 + "), sits in a controller package that refuses a parent unless it is an agentic run ("
                 + gate_text + ")") if continuations and not ungated else \
        ("no controller rebuilds a parent run's spec" if not continuations else "")
    below = [x for x in setters if not x["reaches_floor"]]
    api_path = (f"`d4d api` can hand RunSpec a renderer ({'; '.join(cli_inputs)})" if cli_inputs else
                f"`d4d api` hands RunSpec no renderer (the API default is {defaults['api']})")
    if defaults["api"] >= floor:
        api_path += f"; the API default renderer {defaults['api']} is at or above {floor}"
    if below:
        api_path += ("; every other renderer a controller sets is below " + str(floor) + " ("
                     + ", ".join(f"{where(x)}: {_span(x['renderers'])}" for x in below) + ")")
    if refusal["refused"]:
        api_path += (f"; api_runner.execute refuses renderers {_span(refusal['refused'])} before it runs "
                     f"(api_runner.py:{refusal['line']})")
    api_path += (f"; and `build_phase` refuses the audit phase at renderer >= {floor} on any spec, so an API run "
                 "that reached it would stop at audit, not become a hybrid")
    return {"floor": floor, "setters": setters, "propagating_setters": propagating,
            "continuations": continuations, "gates": [{"at": k, **g} for k, g in sorted(used.items())],
            "ungated_continuations": [c["package"] for c in ungated],
            "uncovered": [where(x) for x in uncovered],
            "api_cli_renderer_inputs": cli_inputs, "default_renderer": defaults,
            "admitted_renderers": admitted, "execute_refuses": refusal,
            "api_reaches_floor": bool(cli_inputs) or defaults["api"] >= floor,
            "runtime_hybrid_possible": bool(ungated or uncovered), "why": why,
            "continuations_text": cont_text, "api_path": api_path}


# ---- follow-up turns (#4058)


def _call_arg(call: ast.Call, fn, name: str):
    """The expression a call passes for parameter `name` of `fn`."""
    for k in call.keywords:
        if k.arg == name:
            return k.value
    params = [x.arg for x in fn.args.posonlyargs + fn.args.args]
    if name in params:
        i = params.index(name)
        if i < len(call.args) and not isinstance(call.args[i], ast.Starred):
            return call.args[i]
    return None


def _defaults(fn) -> dict:
    a = fn.args
    pos = a.posonlyargs + a.args
    out = {x.arg: d for x, d in zip(pos[len(pos) - len(a.defaults):], a.defaults)}
    out.update({x.arg: d for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None})
    return out


def _phase_names(expr, fn, funcs: dict, consts: dict, depth: int = 0) -> set[str]:
    """The phase names a model call's `phase` argument can hold, read through
    local assignments, loop targets (`for ph in PHASES` gives "PHASES", a
    loop over another module constant its names) and what callers pass for
    a parameter. Unreadable is not derived."""
    if depth <= 8:
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return {expr.value}
        if isinstance(expr, ast.JoinedStr):
            return {_render_joined(expr, upper=False)}
        if isinstance(expr, ast.Name):
            values, found = set(), False
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == expr.id for t in n.targets):
                    values |= _phase_names(n.value, fn, funcs, consts, depth + 1)
                    found = True
                elif isinstance(n, (ast.For, ast.comprehension)) and isinstance(n.target, ast.Name) and \
                        n.target.id == expr.id:
                    it = n.iter
                    if isinstance(it, ast.Name) and it.id == "PHASES":
                        values.add("PHASES")
                    elif isinstance(it, ast.Name) and isinstance(consts.get(it.id), tuple) and \
                            all(isinstance(v, str) for v in consts[it.id]):
                        values |= set(consts[it.id])
                    elif isinstance(it, (ast.Tuple, ast.List)) and \
                            all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in it.elts):
                        values |= {e.value for e in it.elts}
                    else:
                        break
                    found = True
            else:
                if expr.id in _params(fn):
                    found = True
                    default = _defaults(fn).get(expr.id)
                    if default is not None:
                        values |= _phase_names(default, fn, funcs, consts, depth + 1)
                    for caller in funcs.values():
                        for c in ast.walk(caller):
                            if isinstance(c, ast.Call) and _attr_or_name(c.func) == fn.name:
                                arg = _call_arg(c, fn, expr.id)
                                if arg is not None:
                                    values |= _phase_names(arg, caller, funcs, consts, depth + 1)
                if found:
                    return values
    raise _not_derived("the follow-up turns", f"the phase of a model call (`{ast.unparse(expr)[:40]}` at "
                       f"api_runner.py:{getattr(expr, 'lineno', '?')}) cannot be read")


def _mentions_condition(test) -> bool:
    return any((isinstance(n, ast.Attribute) and n.attr == "condition")
               or (isinstance(n, ast.Name) and (n.id == "condition" or n.id.endswith("_CONDITIONS")))
               for n in ast.walk(test))


def _guards(fn, target) -> list:
    """The tests of the if, while and conditional expressions in `fn` that
    enclose `target`."""
    parents = {}
    for n in ast.walk(fn):
        for c in ast.iter_child_nodes(n):
            parents[c] = n
    out, cur = [], target
    while cur in parents:
        par = parents[cur]
        if isinstance(par, (ast.If, ast.While, ast.IfExp)) and cur is not par.test:
            out.append(par.test)
        cur = par
    return out


def _plan_scopes(tree: ast.Module, consts: dict) -> dict[str, list[str] | None]:
    """turn -> the conditions that make it (None: every condition), from the
    runner's own list of conditional calls in `plan()`."""
    plan = _function(tree, "plan")
    if plan is None:
        raise _not_derived("which conditions make a follow-up turn", "api_runner.py defines no plan()")
    value = next((v for n in ast.walk(plan) if isinstance(n, ast.Dict) for k, v in zip(n.keys, n.values)
                  if isinstance(k, ast.Constant) and k.value == "conditional_calls"), None)
    if value is None:
        raise _not_derived("which conditions make a follow-up turn", "plan() lists no conditional_calls")
    scopes: dict[str, list[str] | None] = {}

    def gate_of(test):
        for left, op, right in _compares(test):
            if _attr_or_name(left) == "condition":
                if isinstance(op, ast.In) and isinstance(right, ast.Name) and isinstance(consts.get(right.id), tuple):
                    return sorted(consts[right.id])
                if isinstance(op, ast.Eq) and isinstance(right, ast.Constant):
                    return [right.value]
        raise _not_derived("which conditions make a follow-up turn",
                           f"plan() gates a conditional call on `{ast.unparse(test)[:60]}`")

    def visit(node, gate):
        if isinstance(node, ast.IfExp):
            visit(node.body, gate_of(node.test))
            visit(node.orelse, gate)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            m = re.match(r"(\w+):", node.value)
            if m:
                scopes[m.group(1)] = gate
        elif isinstance(node, ast.JoinedStr):
            if node.values and isinstance(node.values[0], ast.Constant):
                visit(node.values[0], gate)
        else:
            for child in ast.iter_child_nodes(node):
                visit(child, gate)

    visit(value, None)
    return scopes


def derive_followups(tree: ast.Module, phases: list[str], consts: dict) -> dict:
    """The model calls an API run can make besides its phases (#4058), read
    from the code: the runner's model-call wrapper (the function taking a
    `phase` that calls the function that sends the request) and the phase
    each call of it names. A turn's conditions come from `plan()`'s
    conditional calls; a turn plan() does not list is made under every
    condition when no condition test guards its call path (its call site and
    its function's callers), and is not derived otherwise."""
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    senders = {name for name, fn in funcs.items()
               if any(isinstance(c, ast.Call) and MODEL_CALL.search(_dotted(c.func)) for c in ast.walk(fn))}
    if not senders:
        raise _not_derived("the model calls", "api_runner.py sends no `client.messages` request")
    wrappers = {name for name, fn in funcs.items() if "phase" in _params(fn) and any(
        isinstance(c, ast.Call) and _attr_or_name(c.func) in senders for c in ast.walk(fn))}
    if not wrappers:
        raise _not_derived("the model calls", "no function taking a `phase` calls the request sender")
    calls: dict[str, list[tuple[str, ast.Call]]] = {}
    for name, fn in funcs.items():
        if name in wrappers or name in senders:
            continue
        for c in ast.walk(fn):
            if not isinstance(c, ast.Call):
                continue
            callee = _attr_or_name(c.func)
            if callee in senders:
                raise _not_derived("the model calls", f"{name}() sends a request outside the phase wrapper "
                                   f"(api_runner.py:{c.lineno})")
            if callee not in wrappers:
                continue
            arg = _call_arg(c, funcs[callee], "phase")
            if arg is None:
                raise _not_derived("the model calls", f"the call at api_runner.py:{c.lineno} names no phase")
            for value in _phase_names(arg, fn, funcs, consts):
                calls.setdefault(value, []).append((name, c))
    if "PHASES" not in calls:
        raise _not_derived("the model phases", "no model call iterates the runner's PHASES")
    scopes = _plan_scopes(tree, consts)
    turns = {}
    for turn, sites in sorted(calls.items()):
        if turn == "PHASES" or turn in phases:
            continue
        if turn in scopes:
            scope, basis = scopes[turn], "per plan()'s conditional_calls"
        else:
            guarded = []
            for fname, c in sites:
                guarded += [t for t in _guards(funcs[fname], c) if _mentions_condition(t)]
                for caller in funcs.values():
                    for cc in ast.walk(caller):
                        if isinstance(cc, ast.Call) and _attr_or_name(cc.func) == fname:
                            guarded += [t for t in _guards(caller, cc) if _mentions_condition(t)]
            if guarded:
                raise _not_derived("which conditions make a follow-up turn",
                                   f"`{turn}` is guarded by `{ast.unparse(guarded[0])[:60]}` and plan() does not "
                                   "list it")
            scope, basis = None, "since no condition test guards its call path"
        turns[turn] = {"calls": sorted({f"api_runner.py:{c.lineno}" for _, c in sites}), "conditions": scope,
                       "basis": basis}
    return turns


def api_meaning(root: Path, facts: dict) -> dict:
    for key in ("conditions", "controllers", "legacy_scripts"):
        if key not in facts:
            raise ConfigError(f"api_meaning needs discover()'s facts; `{key}` is missing")
    tree = _tree(root / RUNNER)
    consts = _module_constants(root / RUNNER)
    cond = facts["conditions"]
    phases = cond["phases"]
    derived = cond["derived_phases"] if cond["core_derived"] else []
    model_phases = [p for p in phases if p not in derived]

    build = _function(tree, "build_phase")
    if build is None:
        raise _not_derived("the phase builder", "api_runner.py defines no build_phase")
    calls = {n.attr for n in ast.walk(build) if isinstance(n, ast.Attribute)} | \
        {n.id for n in ast.walk(build) if isinstance(n, ast.Name)}
    strings = [n.value for n in ast.walk(build) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    if "digest_text" in calls:
        schema_form = "schema digest (schema_digest.digest_text)"
    elif any("_all.yaml" in c for c in strings):
        schema_form = "merged LinkML schema (_all.yaml)"
    else:
        raise _not_derived("the schema form a phase sends", "build_phase names neither digest_text nor _all.yaml")
    full_schema = schema_form.startswith("merged LinkML schema")
    whole_schema = schema_form.startswith("schema digest") and any("_all.yaml" in c for c in strings)
    floor = derive_agentic_audit_from(build)
    continuation = audit_continuations(root, floor, sorted(facts["controllers"]), tree, cond["agentic_runtimes"])
    followups = derive_followups(tree, phases, consts)
    gh = facts.get("github_assistant_run") or {}

    def turns_for(c):
        return sorted(t for t, v in followups.items() if v["conditions"] is None or c in v["conditions"])

    claude_names = {p.stem: _rel(root, p) for d in (".claude/commands", ".claude/agents")
                    for p in sorted((root / d).glob("*.md")) if p.stem.lower() != "readme"}
    tuned = cond.get("tuned") or {}
    conditions = {}
    for name, rel in sorted(cond["prompts"].items()):
        p = root / rel
        if not p.is_file():
            raise _not_derived(f"condition `{name}`", f"its prompt {rel} does not exist")
        body = p.read_text(encoding="utf-8").split("## Prompt body", 1)[-1]
        refs = sorted(_named_claude_files(body, claude_names))
        hybrid = []
        if refs:
            hybrid.append("the prompt body tells the model to read " + ", ".join(refs)
                          + "; the API request never carries those files (a prompt-level hybrid)")
        if continuation["runtime_hybrid_possible"]:
            hybrid.append("a runtime hybrid cannot be ruled out: " + continuation["why"])
        roles = (["current generic"] if name == cond["current"] else []) + \
            (["CLI default"] if name == cond["default"] else []) + \
            (["GitHub assistant"] if gh and name == gh["condition_name"] else []) + \
            (["per-project tuning: inserts " + ", ".join(tuned.get("appends") or ["nothing"])]
             if name == "tuned" else [])
        conditions[name] = {
            "status": "live" if name in cond["live"] else "historical",
            "role": " + ".join(roles),
            "prompt": rel,
            "receipt_condition": name in cond["receipt_conditions"],
            "tuned": name == "tuned",
            "followup_turns": turns_for(name),
            "shape": shape_of(model_phases, turns_for(name), full_schema),
            "model_calls_minimum": len(model_phases),
            "schema_form": schema_form + (" + merged-schema reference" if whole_schema else ""),
            "prompt_hybrid": bool(refs),
            "runtime_hybrid": continuation["runtime_hybrid_possible"],
            "hybrid_reasons": hybrid,
            "prompt_body_references": refs,
            "appends": list(tuned.get("appends") or []) if name == "tuned" else [],
        }

    arms_table = _module_constants(root / CLI_API).get("ARMS")
    if not isinstance(arms_table, dict) or not arms_table:
        raise _not_derived("the API arms", "cli/api.py ARMS is not a module-level dict literal")
    # an arm's shape is the condition's unless the runner branches on the arm (#4058)
    arm_branches = sorted({n.lineno for n in ast.walk(tree) if isinstance(n, (ast.If, ast.IfExp, ast.While, ast.Match))
                           for t in [getattr(n, "test", None) or getattr(n, "subject", None)] if t is not None
                           and any(isinstance(x, ast.Attribute) and x.attr == "arm" for x in ast.walk(t))})
    if arm_branches:
        raise _not_derived("the arms' shape", f"api_runner branches on the arm at line(s) {arm_branches}")
    shapes = sorted({v["shape"] for v in conditions.values()})
    arm_shape = (shapes[0] if len(shapes) == 1 else "the condition's") + \
        " (the arm sets the bundle, method directory and manifest; api_runner never branches on it)"
    arms = {}
    for arm, row in sorted(arms_table.items()):
        arms[arm] = {"method_dir": row[1], "bundle": row[2], "shape": arm_shape,
                     "manifest": row[3].replace("# Source manifest: ", "")}

    legacy = {}
    for rel in facts["legacy_scripts"]:
        text, ltree = _parse(root / rel)
        if ltree is None:           # never "UNPARSED" and left out of the verdict (#4092)
            raise _unparsed([f"{rel} ({_parse_problem(root / rel)})"])
        n_calls = len(model_call_sites(ltree))
        full = bool(re.search(r"_all\.yaml|get_full_schema", text))
        # concatenated input: the file name says so, or it reads the
        # concatenated bundles / the d4d_concatenated prompts (#4023)
        concatenated = "concatenat" in Path(rel).name or bool(
            re.search(r"preprocessed/concatenated|d4d_concatenated_\w*prompt", text))
        tools = re.findall(r"@[\w.]*\.tool(?:_plain)?\b", text)
        shape = ("MONOLITHIC" if n_calls == 1 and full and concatenated and not tools else
                 "MONOLITHIC + TOOLS (hybrid)" if n_calls and full and concatenated else
                 "PER-DOCUMENT" if n_calls and not concatenated else
                 "NO MODEL CALL" if not n_calls else "UNCLEAR")
        legacy[rel] = {"shape": shape, "model_call_sites": n_calls, "full_schema": full,
                       "concatenated_input": concatenated, "tool_decorators": len(tools)}

    gh_row = {}
    if gh:
        gh_row = {**gh, "shape": conditions[gh["condition_name"]]["shape"]}

    rt = _module_constants(root / AGENTIC_RUNTIME).get("SCHEMAS")
    if not isinstance(rt, tuple) or not rt:
        raise _not_derived("the native schema form", "agentic_runtime.SCHEMAS is not a module-level tuple of paths")
    heads = re.findall(r"(?m)^#+\s*(Phase \d+[^\n]*)", (root / PLAYBOOK).read_text(encoding="utf-8"))
    if not heads:
        raise _not_derived("the native phases", f"{PLAYBOOK} has no `Phase N` heading")
    native = {"playbook": PLAYBOOK, "phases": heads[:8],
              "schema_form": "LinkML schema files read whole (agentic_runtime.SCHEMAS: " + ", ".join(rt) + ")",
              "shape": "AGENTIC MULTI-PHASE" if len(heads) > 1 else "AGENTIC SINGLE-PHASE"}

    live = cond["live"]
    mono = [c for c in live if conditions[c]["shape"] == "MONOLITHIC"]
    mono_legacy = sorted(k for k, v in legacy.items() if v["shape"] == "MONOLITHIC")
    verdict = []
    if mono:
        verdict.append("Live API conditions that are MONOLITHIC: " + ", ".join(mono) + ".")
    else:
        why = []
        if len(model_phases) > 1:
            why.append(f"each run makes at least {len(model_phases)} model calls ({', '.join(model_phases)})")
        else:
            why.append(f"each run makes one model call ({', '.join(model_phases)}) before any follow-up turn")
        if not full_schema:
            why.append(f"it sends the {schema_form} rather than the LinkML schema")
        every = sorted(t for t, v in followups.items() if v["conditions"] is None)
        if every:
            why.append("every condition may add " + ", ".join(every) + " turns")
        for t, v in sorted(followups.items()):
            if v["conditions"] is not None:
                live_in = [c for c in live if c in v["conditions"]]
                why.append(f"{t} runs only under {', '.join(v['conditions'])} ("
                           + (f"of the live ones, {', '.join(live_in)}" if live_in else "no live condition") + ")")
        verdict.append(f"No live API condition ({', '.join(live)}) is monolithic: " + "; ".join(why) + ".")
    if mono_legacy:
        verdict.append("The monolithic shape (prompt + full LinkML schema + concatenated documents, one call) "
                       f"survives only in {len(mono_legacy)} scripts outside the runner: "
                       + ", ".join(mono_legacy) + ".")
    else:
        verdict.append("No script outside the runner has the monolithic shape.")
    prompt_hybrids = sorted(c for c in live if conditions[c]["prompt_hybrid"])
    if prompt_hybrids:
        verdict.append("Prompt-level hybrid: the live conditions " + ", ".join(prompt_hybrids) + " tell the "
                       "API model to read playbook files the API request never carries ("
                       + ", ".join(sorted({r for c in prompt_hybrids for r in conditions[c]["prompt_body_references"]}))
                       + ").")
    if continuation["runtime_hybrid_possible"]:
        verdict.append("A runtime hybrid (an API run part of which a native agent does) cannot be ruled out: "
                       + continuation["why"] + ".")
    else:
        verdict.append("No API condition is a runtime hybrid: " + "; ".join(
            t for t in (continuation["continuations_text"], continuation["why"], continuation["api_path"]) if t)
            + ".")
    verdict.append("The agentic runtimes " + ", ".join(cond["agentic_runtimes"]) + " render the same condition "
                   "names (one name, two procedures); a run is one or the other, not a hybrid.")
    return {"definition": ("api = MONOLITHIC: one model call whose input is the prompt, the full LinkML "
                           "schema and the input documents concatenated with separators"),
            "phases": phases, "derived_phases": derived, "model_phases": model_phases,
            "schema_form": schema_form, "followup_turns": followups,
            "agentic_audit_from_renderer": floor,
            "default_renderer": continuation["default_renderer"],
            "audit_continuations": continuation,
            "agentic_runtimes": cond["agentic_runtimes"],
            "conditions": conditions, "arms": arms, "legacy": legacy,
            "github_assistant": gh_row, "native": native, "verdict": verdict}


# --------------------------------------------------------------------------
# report


def _git_head(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def exit_status(self_test_passed: bool, violations: list) -> int:
    """2 when the self-test failed (the scan cannot vouch for what it did not
    see), 1 when there is a violation, else 0 (#4057)."""
    if not self_test_passed:
        return 2
    return 1 if violations else 0


def run(root: Path, tokens_file: Path = TOKENS_FILE, exceptions_file: Path = EXCEPTIONS_FILE) -> dict:
    tokens = load_tokens(root, tokens_file)
    st = self_test(tokens)
    if not st["passed"]:
        return {"self_test": st, "exit": exit_status(False, [])}
    exceptions = load_exceptions(exceptions_file)
    surfaces, facts = discover(root)
    hits, unreadable, unparsed = [], [], []
    for rel in sorted(surfaces.files):
        try:
            hits.extend(scan_file(root, surfaces.files[rel], tokens))
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{rel} ({type(exc).__name__})")
        except UnparsedSurface as exc:
            unparsed.append(str(exc))
    if unreadable:
        raise ConfigError("discovered surfaces could not be read, so the scan cannot vouch for them: "
                          + "; ".join(unreadable))
    if unparsed:            # a Python surface that does not parse is never "nothing gates" (#4092)
        raise _unparsed(unparsed)
    used = {}
    for h in hits:
        e = exception_for(h, exceptions)
        h["exception"] = None if e is None else e["_index"]
        if e is not None:
            used[e["_index"]] = used.get(e["_index"], 0) + 1
        h["violation"] = is_violation(h)
    tests, own_tests = scan_tests(root, tokens)
    facts["tests_of_this_audit"] = own_tests
    meaning = api_meaning(root, facts)
    violations = [h for h in hits if h["violation"]]
    return {"root": root.name, "commit": _git_head(root), "self_test": st,
            "surfaces": {k: v.as_dict() for k, v in sorted(surfaces.files.items())}, "facts": facts,
            "exceptions": [{k: v for k, v in e.items() if not k.startswith("_")} | {"index": e["_index"],
                           "hits": used.get(e["_index"], 0)} for e in exceptions],
            "hits": hits, "violations": violations, "test_dependencies": tests,
            "api_meaning": meaning, "exit": exit_status(True, violations)}


def summarize(result: dict) -> dict:
    """The JSON summary: every violation, every gc_project hit, every tracked
    hit that is model-facing or code-level with no recorded reason, and
    per-file counts for the rest. `--full-json` writes every hit instead."""
    if result["exit"] == 2:
        return result
    hits = result["hits"]
    counts: dict[str, dict] = {}
    for h in hits:
        key = f"{h['path']}|{h['category']}"
        row = counts.setdefault(key, {"path": h["path"], "category": h["category"],
                                      "approaches": h["approaches"], "hits": 0, "model_facing": 0,
                                      "with_reason": 0, "contexts": {}})
        row["hits"] += 1
        row["model_facing"] += h["model_facing"]
        row["with_reason"] += h["exception"] is not None
        row["contexts"][h["context"]] = row["contexts"].get(h["context"], 0) + 1
    out = {k: v for k, v in result.items() if k != "hits"}
    out["gc_project_hits"] = [h for h in hits if h["category"] == "gc_project"]
    out["tracked_without_reason"] = [h for h in hits if h["category"] in TRACKED
                                     and h["exception"] is None and (h["model_facing"] or h["code"])]
    out["counts_by_file"] = sorted(counts.values(), key=lambda r: (r["path"], r["category"]))
    out["totals"] = {c: {"hits": sum(h["category"] == c for h in hits),
                         "model_facing": sum(h["category"] == c and h["model_facing"] for h in hits),
                         "with_reason": sum(h["category"] == c and h["exception"] is not None for h in hits)}
                     for c in CATEGORIES}
    out["totals"]["violations"] = len(result["violations"])
    out["totals"]["violations_by_approach"] = {a: sum(a in h["gates_in"] for h in result["violations"])
                                               for a in APPROACHES}
    return out


def _table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return out


def _why_quiet(h: dict) -> str:
    if h["exception"] is not None:
        return f"exception #{h['exception']}"
    if h.get("main_block") and (h["context"] in CODE_CONTEXTS or h["context"] in MODEL_FACING_CONTEXTS):
        return "`__main__` block of a module the gating approaches only import"
    if h["role"] == "exposed":
        return "exposed"
    if not any(APPROACHES[a][0] for a in h["approaches"]):
        return "non-gating approach (" + ", ".join(h["approaches"]) + ")"
    return h["context"]


def _session_statement(it: dict) -> str:
    """What the report may say about registered runs and session
    customizations, derived from each launch's flags (#4092, #4131, #4156):
    unaffected only where every registered native launch is shown to pass
    `--safe-mode`, as a literal element of the argv list it hands over.
    `--bare` skips CLAUDE.md and the settings hooks but leaves skills
    resolving, so a launch with `--bare` alone still lists the command,
    agent and skill descriptions."""
    launches = it.get("launches") or []
    if not launches:
        return ("No run controller launches a native runtime with a system prompt or a system-prompt file, so no "
                "registered native run is affected; the interactive_session approach covers interactive sessions.")
    ok = [x for x in launches if x["carries"]]
    if len(ok) == len(launches):
        return ("Every registered native launch passes `--safe-mode`, which switches these off: " + "; ".join(
            f"`{x['site']}` (" + "; ".join(x["evidence"]) + ")" for x in launches)
            + ". So the interactive_session approach covers interactive sessions only; it does not change a "
            "registered run's verdict.")
    bad = [x for x in launches if not x["carries"]]

    def why(x):
        said = ("has no `--safe-mode` element" if x["carries"] is False else
                "cannot be shown to pass `--safe-mode`") + " (" + "; ".join(x["evidence"]) + ")"
        if x.get("memory_off"):
            return said + "; it passes `--bare` (" + "; ".join(x["memory_evidence"]) + \
                "), which skips CLAUDE.md and the settings hooks but still lists the commands, agents and skills"
        return said + ("; nor a `--bare` element" if x.get("memory_off") is False else
                       "; nor can it be shown to pass `--bare`")
    return ("NOT every registered native launch is shown to pass `--safe-mode` (a launch is shown to pass it only "
            "where the literal is an element of the argv list the launch hands over, unchanged): " + "; ".join(
                f"`{x['site']}` " + why(x) for x in bad)
            + (". The others are: " + "; ".join(f"`{x['site']}`" for x in ok) if ok else "")
            + ". A run so launched may load what an interactive session loads and it is not shown to switch off, so "
            "those interactive_session surfaces are also run_controllers surfaces, and their violations count there.")


def _unused_exceptions(exceptions: list[dict], surfaces) -> str | None:
    """The report line for exceptions no hit used: stale, or the finding was
    fixed, unless the entry names no surface of the scanned checkout (an
    exception added with the file it covers, read on an older tree)."""
    unused = [e for e in exceptions if e["hits"] == 0]
    if not unused:
        return None

    def absent(e):
        globs = [e["path"]] if isinstance(e["path"], str) else e["path"]
        return not any(fnmatch.fnmatchcase(p, g) for p in surfaces for g in globs)
    return "Unused exceptions (stale, or the finding was fixed): " + ", ".join(
        f"#{e['index']}" + (" (names no surface of this checkout)" if absent(e) else "") for e in unused)


def render_markdown(result: dict) -> str:
    L = ["# D4D generation-specificity audit", ""]
    st = result["self_test"]
    python = (result.get("facts") or {}).get("python")
    L += [f"Checkout `{result.get('root')}` at commit `{result.get('commit')}`; generated by "
          f"`.claude/skills/d4d-generation-specificity-audit/scan.py`" + (f" under {python}" if python else "") + ".",
          f"Self-test: {'passed' if st['passed'] else 'FAILED'} "
          f"(tokens by category: {st['token_counts']}; {st['imported_from_neutrality_test']} imported from "
          f"`{NEUTRALITY_TEST}`).", ""]
    if result["exit"] == 2:
        return "\n".join(L + ["Self-test problems:"] + [f"- {p}" for p in st["problems"]]) + "\n"
    hits, viol = result["hits"], result["violations"]
    L += [f"Exit status: **{result['exit']}** — {len(viol)} gc_project violation(s).", ""]

    L += ["## Surfaces", ""]
    rows = []
    for a, (gates, desc) in APPROACHES.items():
        files = [s for s in result["surfaces"].values() if a in s["approaches"]]
        by = {r: sum(s["roles"].get(a) == r for s in files) for r in ROLE_RANK}
        rows.append([a, "yes" if gates else "no", len(files), by["model_facing"], by["exposed"],
                     by["run_shaping"], sum(a in h["gates_in"] for h in viol), desc])
    L += _table(rows, ["approach", "gates exit", "files", "model-facing", "exposed", "run-shaping",
                       "violations", "what"]) + [""]

    f = result["facts"]
    tc = f["toolchain"]
    it = f["interactive"]
    roots = f["python_roots"]
    runs = f.get("controller_runs") or {}
    ai = f.get("assistant_instructions") or {}
    L += ["## How the surfaces were found", "",
          f"- Python modules read: {len(f['python_sources'])} non-test modules under "
          + ", ".join(f"`{r}/`" for r in roots)
          + f" ({f['registered_copies_skipped']} registered byte copies under `registrations/` skipped). Every "
          "one parses; a file that does not stops the scan (exit 2).",
          "- What a native run is handed (`agentic_runtime.toolchain()`, read with ast): the schemas "
          + ", ".join(f"`{x}`" for x in tc["schemas"]) + " and `" + tc["pattern"] + "` in "
          + ", ".join(f"`{d}`" for d in tc["directories"])
          + (". It hands no Python file, so a script is a surface only where a playbook, agent, controller "
             "or arm command runs or imports it." if not fnmatch.fnmatch("x.py", tc["pattern"]) else
             ". It hands Python files too: each is exposed unless something live names it."),
          f"- Run controllers and launchers: {len(f['controllers'])} modules. A seed under `notes/` builds a "
          "generation request; one under `scripts/` or `src/` (outside the generation closures) also launches "
          "it; the rest are imported by a controller or run one (imports one, or stages its files by name). "
          f"{sum(bool(v) for v in runs.values())} of them run as a script (an argv runs them, a document beside "
          "them runs them, nothing imports them, or their own `__main__` block calls a function that launches a run "
          "or a command-line interface nothing else calls); a `__main__` block counts only in those.",
          "- Text a controller hands to the model: "
          + (", ".join(f"`{k}`" for k in f["controller_text"]) or "none") + ".",
          "- Code whose text reaches a model, found by data flow from `--system-prompt`, from the hook fields "
          "Claude Code shows the model (a PreToolUse deny reason, and the classifier reasons that feed it) and "
          "from the functions that render model text: "
          + ("; ".join(f"`{k}`: " + ", ".join(v) for k, v in f["model_text"].items()) or "none") + ".",
          "- Playbooks and agents a playbook, a live prompt, a controller or an assistant instruction names "
          "(path, bare name or slash command): " + ", ".join(f"`{r}`" for r in f["native_referenced"]) + ".",
          "- Assistant instruction files, a surface only where the `@d4dassistant` workflow, a playbook or a "
          "loaded instruction loads them: " + ("; ".join(f"`{k}` (" + (", ".join(
              "loaded by " + re.sub(r"^(\S+) \((\w+)\)$", r"`\1` (\2)", x) for x in v)
              or "loaded by nothing: not a surface") + ")" for k, v in ai.items()) or "none") + ".",
          f"- Other files they name ({len(f['named_files'])}): "
          + "; ".join(f"`{k}` ({', '.join(v['approaches'])}{', run' if v['runs'] else ''})"
                      for k, v in f["named_files"].items()) + ".",
          "- What the scripts they and the hooks run import (`python x.py`, `-m`; a closure stops at the CLI "
          "package and at the upstream input): " + ("; ".join(f"`{k}`: " + ", ".join(f"`{x}`" for x in v)
                                                               for k, v in f["run_script_imports"].items())
                                                     or "nothing") + ".",
          "- CLI groups they run (`d4d <group> ...`), each followed through its imports: "
          + ("; ".join(f"{a}: " + ", ".join(f"`{g}`" + (" (exposed)" if v["role"] == "exposed" else "")
                                            for g, v in gs.items()) for a, gs in f["cli_groups"].items())
             or "none") + ".",
          "- Interactive sessions: Claude Code loads the project memory "
          + (", ".join(f"`{m}`" for m in it["memory"]) or "(none)")
          + (f" (named by {', '.join(f'`{n}`' for n in it['memory_named_by'])})" if it["memory_named_by"] else "")
          + ", the settings " + (", ".join(f"`{x}`" for x in it["settings"]) or "(none)")
          + " and their hooks " + (", ".join(f"`{x}`" for x in it["hooks"]) or "(none)")
          + f", and lists the name and description of {len(it['described'])} commands, agents and skills "
          "(their bodies load when invoked). " + _session_statement(it),
          "- Deterministic arm commands (CLI groups that name a non-baseline arm's bundle): "
          + "; ".join(f"`{k}` ({v})" for k, v in f["deterministic_commands"].items())
          + f". Their import closure: {len(f['deterministic_closure'])} modules, following "
          "`data_sheets_schema`, `src.*` and the directories the code puts on sys.path ("
          + (", ".join(f"`{d}`" for d in f["deterministic_sys_path"]) or "none") + ").",
          "- Upstream input (the `d4d download` group's `src.download` imports): "
          + (", ".join(f"`{k}`" for k in f["shared_input"]) or "none") + ".",
          "- Legacy prompt sets beside the conditions: " + ", ".join(f"`{d}`" for d in f["legacy_prompt_sets"])
          + ".",
          ""]
    L += _table([[f"`{p}`", w, runs.get(p) or "no: imported only"] for p, w in f["controllers"].items()],
                ["run controller", "why", "runs as a script"]) + [""]
    L += _table([[f"`{p}`", ", ".join(v["evidence"]), v["classified"]] for p, v in f["model_clients"].items()],
                ["module that calls a model client", "evidence", "classified as"]) + [""]
    if f["evaluation_controllers"]:
        L += ["Evaluation controllers (listed under other_model_client, never gating): "
              + ", ".join(f"`{p}`" for p in f["evaluation_controllers"]) + ".", ""]

    L += ["## gc_project violations", "",
          "A Grand Challenge project's name, site or identifier in model-facing text or in a code "
          "branch/table of a generation surface, with no tracked exception. Fix each: move the fact "
          "into the manifest or profile, or remove it.", ""]
    if viol:
        L += _table([[f"`{h['path']}:{h['line']}`", ",".join(h["gates_in"]), h["status"],
                      h["context"] + (f" in {h['model_text_function']}" if h.get("model_text_function") else ""),
                      f"`{h['match']}`", h["snippet"][:110]] for h in viol],
                    ["where", "approach", "status", "context", "token", "line"])
    else:
        L.append("None.")
    L.append("")

    L += ["## Tracked categories", "",
          "Bridge2AI-program and biomedical/clinical hits never fail the run. Each needs a recorded "
          "reason in `exceptions.yaml`; the second table lists the files whose hits have none.", ""]
    rows = []
    for cat in TRACKED:
        for a in APPROACHES:
            hs = [h for h in hits if h["category"] == cat and a in h["approaches"]]
            if not hs:
                continue
            rows.append([cat, a, len(hs), sum(h["model_facing"] for h in hs),
                         sum(h["exception"] is not None for h in hs),
                         sum(h["exception"] is None for h in hs)])
    L += _table(rows, ["category", "approach", "hits", "model-facing", "with reason", "no reason"]) + [""]
    unreasoned: dict[tuple, list] = {}
    for h in hits:
        if h["category"] in TRACKED and h["exception"] is None and (h["model_facing"] or h["code"]):
            unreasoned.setdefault((h["path"], h["category"]), []).append(h)
    if unreasoned:
        L += ["Model-facing or code-level tracked hits with no recorded reason (file, category, count, "
              "first lines, tokens):", ""]
        L += _table([[f"`{p}`", c, len(v), ", ".join(str(h["line"]) for h in v[:6]),
                      ", ".join(sorted({h["match"].lower() for h in v}))[:120]]
                     for (p, c), v in sorted(unreasoned.items())],
                    ["file", "category", "hits", "lines", "tokens"]) + [""]

    L += ["## gc_project hits that do not fail", "",
          "Excepted, in comments/docstrings/headers, in run-shaping literals, in `__main__` blocks of "
          "modules the gating approaches only import, in files the native toolchain exposes but no "
          "playbook names, or in a non-gating approach (upstream input, other model clients).", ""]
    quiet: dict[tuple, list] = {}
    for h in hits:
        if h["category"] == "gc_project" and not h["violation"]:
            quiet.setdefault((h["path"], _why_quiet(h)), []).append(h)
    L += _table([[f"`{p}`", w, len(v), ", ".join(str(h["line"]) for h in v[:8]),
                  ", ".join(sorted({h["match"] for h in v}))[:100]] for (p, w), v in sorted(quiet.items())],
                ["file", "why not failing", "hits", "lines", "tokens"]) + [""]

    L += ["## Tests asserting project-dependent generation behaviour", ""]
    td = result["test_dependencies"]
    if td:
        agg: dict[str, list] = {}
        for t in td:
            agg.setdefault(t["path"], []).append(t)
        L += _table([[f"`{p}`", len(v), ", ".join(str(t["line"]) for t in v[:8]),
                      ", ".join(sorted({t["match"] for t in v}))] for p, v in sorted(agg.items())],
                    ["test file", "asserted literals", "lines", "tokens"])
    else:
        L.append("None.")
    if f.get("tests_of_this_audit"):
        L += ["", "Not listed: the tests of this audit (they plant tokens to check the scanner): "
              + ", ".join(f"`{t}`" for t in f["tests_of_this_audit"]) + "."]
    L.append("")

    L += ["## Exceptions", ""]
    L += _table([[e["index"], e["path"], e.get("token") or "", e.get("category") or "", e["hits"],
                  e["reason"][:140], e["decision"]] for e in result["exceptions"]],
                ["#", "path", "token", "category", "hits", "reason", "decision"]) + [""]
    unused = _unused_exceptions(result["exceptions"], result["surfaces"])
    if unused:
        L += [unused, ""]

    m = result["api_meaning"]
    ac = m["audit_continuations"]
    L += ["## What \"api\" means in the code", "", f"Definition checked: {m['definition']}.", ""]
    L += [f"- Phases (`api_runner.PHASES`): {', '.join(m['phases'])}; derived without a model call: "
          f"{', '.join(m['derived_phases']) or 'none'}; model phases: {', '.join(m['model_phases'])}.",
          f"- Schema sent: {m['schema_form']}.",
          "- Follow-up turns (model calls besides the phases, from the runner's model-call wrapper): "
          + "; ".join(f"{k} ({', '.join(v['calls'])}; " + ("every condition" if v["conditions"] is None
                      else "only " + ", ".join(v["conditions"])) + f", {v['basis']})"
                      for k, v in m["followup_turns"].items()) + ".",
          f"- Native audit batch: from renderer {m['agentic_audit_from_renderer']}, `build_phase` refuses the "
          f"audit phase on every spec and the audit is a registered native batch. Default renderer when none is "
          f"registered: {m['default_renderer']['api']} for the API runtime, {m['default_renderer']['agentic']} "
          f"for an agentic one. RunSpec admits renderers {_span(ac['admitted_renderers'])}.",
          "- Native continuations of a parent run (controllers that rebuild its spec, any renderer): "
          + ("; ".join(f"`{c['package']}` (" + (", ".join(c["gates"]) or "NO agentic-parent gate") + ")"
                       for c in ac["continuations"]) or "none") + ".",
          f"- Who reaches renderer {ac['floor']} or above: {ac['why']}. {ac['api_path'][0].upper()}"
          f"{ac['api_path'][1:]}.",
          f"- Agentic runtimes that render the same condition names (one name, two procedures; not a hybrid "
          f"run): {', '.join(m['agentic_runtimes'])}.", ""]
    L += _table([[f"`{x['path']}:{x['line']}`", _span(x["renderers"]), x["origin"], x["runtime"] or "",
                  "yes" if x["reaches_floor"] else "no", x["covered"] or "NOT COVERED"] for x in ac["setters"]],
                ["renderer setter", "renderers", "origin", "runtime", f"reaches {ac['floor']}", "covered by"]) + [""]
    L += [f"{ac['propagating_setters']} further setters pass on a renderer recorded or registered elsewhere "
          "(a record, a registration, a spec or a caller).", ""]
    L += _table([[c, v["status"], v["role"], v["shape"], v["model_calls_minimum"],
                  ", ".join(v["followup_turns"]) or "none",
                  "yes" if v["receipt_condition"] else "", "yes" if v["prompt_hybrid"] else "no",
                  "possible" if v["runtime_hybrid"] else "no", ", ".join(v["prompt_body_references"])]
                 for c, v in m["conditions"].items()],
                ["condition", "status", "role", "shape", "min model calls", "follow-up turns", "receipt",
                 "prompt-level hybrid", "runtime hybrid", "playbook files the body names"]) + [""]
    reasons = sorted({r for v in m["conditions"].values() for r in v["hybrid_reasons"]})
    if reasons:
        L += ["Why a condition is a prompt-level or runtime hybrid: " + "; ".join(reasons) + ".", ""]
    L += _table([[a, v["method_dir"], v["bundle"], v["shape"]] for a, v in m["arms"].items()],
                ["arm", "method dir", "bundle", "shape"]) + [""]
    L += _table([[f"`{p}`", v["shape"], v["model_call_sites"], v["full_schema"], v["concatenated_input"],
                  v["tool_decorators"]] for p, v in m["legacy"].items()],
                ["script outside the runner", "shape", "call sites", "full schema", "concatenated input",
                 "tools"]) + [""]
    gh = m["github_assistant"]
    if gh:
        L += [f"GitHub assistant: `{gh['command']}` — condition {gh['condition']}; manifest "
              f"{gh['manifest']}; shape {gh['shape']}.", ""]
    else:
        L += ["GitHub assistant: no `.github/workflows/d4d-agent.yml`.", ""]
    nv = m["native"]
    L += [f"Native: `{nv['playbook']}` — {nv['shape']}; {nv['schema_form']}; "
          f"{len(nv['phases'])} phase headings.", ""]
    L += ["Verdict:", ""] + [f"- {v}" for v in m["verdict"]] + [""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--report", type=Path, help="markdown report path (default: a temp dir)")
    ap.add_argument("--json", type=Path, help="JSON summary path (default: beside the report)")
    ap.add_argument("--tokens", type=Path, default=TOKENS_FILE)
    ap.add_argument("--exceptions", type=Path, default=EXCEPTIONS_FILE)
    ap.add_argument("--self-test-only", action="store_true")
    ap.add_argument("--full-json", action="store_true", help="write every hit, not the summary")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    # Exit 1 means violations were found, so every way the scan can fail to
    # happen is exit 2: a configuration or derivation error, an unreadable
    # file, and any unexpected error (a traceback is printed, never read as a
    # result).
    try:
        if args.self_test_only:
            st = self_test(load_tokens(root, args.tokens))
            print(json.dumps(st, indent=2))
            return 0 if st["passed"] else 2
        result = run(root, args.tokens, args.exceptions)
        report = args.report or Path(tempfile.mkdtemp(prefix="d4d-specificity-")) / "generation_specificity_audit.md"
        js = args.json or report.with_suffix(".json")
        report.parent.mkdir(parents=True, exist_ok=True)
        js.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(render_markdown(result), encoding="utf-8")
        payload = result if args.full_json else summarize(result)
        js.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    except (ConfigError, ValueError, OSError, yaml.YAMLError, re.error, SyntaxError) as exc:
        print(f"configuration error (exit 2, the scan did not happen): {exc}", file=sys.stderr)
        return 2
    except Exception:                       # noqa: BLE001 — a crash must not read as violations
        traceback.print_exc()
        print("scan failed (exit 2, the scan did not happen): an unexpected error stopped it", file=sys.stderr)
        return 2
    print(f"report: {report}\njson:   {js}")
    print(f"violations: {len(result.get('violations', []))}; exit {result['exit']}")
    return result["exit"]


if __name__ == "__main__":
    sys.exit(main())
