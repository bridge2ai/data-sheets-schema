#!/usr/bin/env python3
"""Generation-specificity audit (#4007): deterministic, offline, stdlib + PyYAML.

Finds text and code in the D4D generation process that is specific to a
Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program
(tracked) or to biomedical/clinical data (tracked), and reports what "api"
means in the code: one monolithic call or several phases, and whether any
step of an API run is agentic.

    python .claude/skills/d4d-generation-specificity-audit/scan.py \
        --report notes/x.md --json notes/x.json

Exit status: 0 when no gc_project hit outside an exception is model-facing or
a code branch/table in a gating surface; 1 when one is; 2 when the scan did
not happen: the self-test failed, the configuration is malformed, a
discovered surface could not be read, a derivation the report rests on found
nothing ("not derived"), or the scan stopped on an error. A crash is never
exit 1, which means violations (#4027).

Nothing here imports the project package: the runner's tables are read with
`ast`, so the audit runs from any checkout without its dependencies and never
executes generation code.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import fnmatch
import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SKILL_DIR.parents[2]
TOKENS_FILE = SKILL_DIR / "tokens.yaml"
EXCEPTIONS_FILE = SKILL_DIR / "exceptions.yaml"
NEUTRALITY_TEST = "tests/test_neutral_generation_schema.py"
RUNNER = "src/data_sheets_schema/api_runner.py"
CLI_API = "src/data_sheets_schema/cli/api.py"
CATEGORIES = ("gc_project", "bridge2ai_program", "biomedical_clinical")
TRACKED = ("bridge2ai_program", "biomedical_clinical")

APPROACHES = {
    # name: (gates the exit status, description)
    "native_agentic": (True, "Claude Code / native runtime following the d4d playbooks and the agents they name"),
    "api": (True, "d4d api run|batch: api_runner and its condition prompts"),
    "github_assistant": (True, "the @d4dassistant workflow and its instruction files"),
    "shared_schema": (True, "the LinkML generation schema, digest inputs, profile and manifest"),
    "deterministic": (True, "the healthsheet and RO-Crate arms that build bundles or records"),
    "run_controllers": (True, "registered-run controllers under notes/ that build a generation request, the "
                              "notes/ modules they import and the launchers that run them"),
    "legacy_monolithic": (True, "generators outside the runner that call a model client to write a D4D record, "
                                "the pre-runner helper scripts and their prompt sets"),
    "shared_input": (False, "download/preprocess/concatenate, upstream of every approach"),
    "other_model_client": (False, "reaches a model outside generation: diagnostic probes, evaluators and "
                                  "evaluation controllers, non-D4D extractors. Listed, never gates"),
}

#: Modules whose text reaches a model (prompt assembly, bundle text, digest).
#: The one hand-kept list: which modules belong to each closure is derived
#: from imports; whether a module *writes model-facing text* is not derivable
#: from an import graph. tests/test_generation_specificity_skill.py fails when
#: a name here is no longer in any discovered closure.
MODEL_FACING_MODULES = frozenset({
    "api_runner", "schema_digest", "schema_semantics", "source_review", "grounding",
    "scope", "source_priority", "source_metadata", "chunking", "evidence_assertions",
    "agentic_runtime", "audit_batch_context", "audit_batch_format", "audit_grammar",
    "healthsheet", "rocrate_normalize",
})

ROLE_RANK = {"model_facing": 3, "exposed": 2, "run_shaping": 1}
MODEL_FACING_CONTEXTS = {"string_literal", "prose", "example", "instruction", "frontmatter", "value"}
CODE_CONTEXTS = {"code_branch", "code_table"}
EXAMPLE_MARK = re.compile(r"\be\.g\.|\bexample|\bsuch as\b|\bfor instance\b|\bi\.e\.", re.I)
MODAL = re.compile(r"\b(must|should|never|always|do not|don't|required?|prefer|use|read|write|"
                   r"record|include|omit|state)\b", re.I)
CLAUDE_REF = re.compile(r"\.claude/(?:commands|agents)/[\w.-]+\.md")
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".config", ".py"}

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
#: receives (render_instruction, render_system, child_system, instruction).
MODEL_TEXT_FUNCTION = re.compile(r"^(?!verify_|check_)(?:render_\w+|\w*instruction|\w*_system|\w*prompt\w*)$")
#: A registered byte copy kept as run evidence (notes/<run>/registrations/...,
#: .../files/src/...): frozen, never executed, never a surface.
REGISTERED_COPY = re.compile(r"(?:^|/)registrations/|(?:^|/)files/(?:src|scripts|notes|tests|\.claude)/")
#: A path that says the module evaluates records rather than generating one.
EVALUATION_PATH = re.compile(r"evaluat", re.I)
#: A module outside every closure that names D4D or a datasheet and calls a
#: model client writes a D4D record: a generator outside the runner.
GENERATOR_TEXT = re.compile(r"d4d|datasheet", re.I)


class ConfigError(ValueError):
    """The configuration, a surface or a derivation failed: the scan did not
    happen (exit 2)."""


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


#: Calls whose literal arguments are a collection: frozenset({"A"}), set(["B"]).
_COLLECTION_CALLS = {"frozenset", "set", "tuple", "list", "sorted", "dict"}
#: Lookups: every constant argument is a key or a default (d.get(p, "A"),
#: os.getenv("X", "A"), getattr(o, "A")).
_LOOKUPS = {"get", "setdefault", "pop", "getenv", "getattr", "hasattr"}


def _table_constants(node):
    """The bare-token constants a value holds when the value is a table, a
    default or a key: a bare token itself, or a literal collection (also
    through frozenset(), set(), tuple(), list(), a conditional expression) of
    bare tokens. A sentence is text, not a table entry, and is never yielded."""
    if node is None:
        return
    if _bare_token(node):
        yield node
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for e in node.elts:
            yield from _table_constants(e)
    elif isinstance(node, ast.Dict):
        for v in node.values:
            yield from _table_constants(v)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _COLLECTION_CALLS:
        for a in node.args:
            yield from _table_constants(a)
    elif isinstance(node, ast.IfExp):
        yield from _table_constants(node.body)
        yield from _table_constants(node.orelse)
    elif isinstance(node, ast.Starred):
        yield from _table_constants(node.value)


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


def _string_lines(node, toks: list, starts: list, lines: list[str]) -> list[tuple[int, str]] | None:
    """(physical line, text) for each line of a string constant, read from
    the STRING tokens that spell it. Implicit concatenation ("a" "b" across
    lines) folds into one value with no newline, so splitting the value alone
    reports every part at the first line (#4026). None when the literal is not
    spelled by plain STRING tokens (an f-string part), or when the tokens
    found do not spell exactly the constant's value."""
    def char_pos(lineno, byte_col):
        return (lineno, _char_col(lines[lineno - 1], byte_col) if 0 < lineno <= len(lines) else byte_col)

    lo = bisect.bisect_left(starts, char_pos(node.lineno, node.col_offset))
    end = char_pos(node.end_lineno, node.end_col_offset)
    parts, values = [], []
    for tok in toks[lo:]:
        if tok.start >= end:
            break
        if tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            continue
        if tok.type != tokenize.STRING:
            return None
        value = _token_value(tok.string)
        if not isinstance(value, str):
            return None
        values.append(value)
        parts += _token_lines(tok, value)
    if not parts or "".join(values) != node.value:
        return None
    return parts


def _python_units(text: str):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for i, line in enumerate(text.splitlines(), 1):
            yield i, "unparsed", line, line
        return
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
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                node.func.attr in {"startswith", "endswith", "__contains__"}:
            branch.update(id(n) for a in node.args for n in ast.walk(a) if isinstance(n, ast.Constant))
        if isinstance(node, ast.Dict):
            table.update(id(k) for k in node.keys if isinstance(k, ast.Constant))
            # a bare-token value is configuration ({"profile": "bridge2ai"}),
            # a value with spaces is text and stays a string literal
            table.update(id(v) for v in node.values if _bare_token(v))
        # Tables, defaults and keys, at any depth and in any file (#4024):
        # assignments (module constants, function locals, attributes), loop
        # and comprehension iterables, every keyword argument, parameter
        # defaults, returned values, subscript keys, lookup keys and defaults,
        # and collection calls (frozenset({...}) wherever it appears).
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            tabled(node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            tabled(node.iter)
        elif isinstance(node, ast.keyword):
            tabled(node.value)          # project="CHORUS", default="CHORUS", choices=["CM4AI"]
        elif isinstance(node, ast.arguments):
            for d in list(node.defaults) + [d for d in node.kw_defaults if d is not None]:
                tabled(d)
        elif isinstance(node, ast.Return):
            tabled(node.value)
        elif isinstance(node, ast.Subscript):
            tabled(node.slice)          # CASES["AI_READI"]
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if name in _LOOKUPS or name in _COLLECTION_CALLS:
                for a in node.args:
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
        if any(k in _EXAMPLE_KEYS for k in keys):
            context = "example"
        elif keys and keys[-1] in _PROSE_KEYS:
            # only the governing key decides: a slot *named* `title` is not prose
            context = "prose"
        else:
            context = "value"
        yield i, context, body, line
        if comment:
            yield i, "comment", comment, line


def units_for(path: Path, rel: str, text: str):
    suffix = path.suffix.lower()
    if suffix == ".py":
        return _python_units(text)
    if suffix in {".md", ".txt"}:
        return _markdown_units(text, prompt_header=rel.startswith("src/download/prompts/")
                               and "## Prompt body" in text)
    if suffix in {".yaml", ".yml", ".config"}:
        return _yaml_units(text)
    return ((i, "value", line, line) for i, line in enumerate(text.splitlines(), 1))


# --------------------------------------------------------------------------
# surfaces


@dataclass
class Surface:
    path: str
    approaches: list[str]
    role: str
    status: str
    why: str


class Surfaces:
    def __init__(self):
        self.files: dict[str, Surface] = {}

    def add(self, rel: str, approach: str, role: str, status: str, why: str):
        cur = self.files.get(rel)
        if cur is None:
            self.files[rel] = Surface(rel, [approach], role, status, why)
            return
        if approach not in cur.approaches:
            cur.approaches.append(approach)
        if ROLE_RANK[role] > ROLE_RANK[cur.role]:
            cur.role, cur.why = role, why
        if cur.status != "live" and status == "live":
            cur.status = status


def _rel(root: Path, p: Path) -> str:
    return p.resolve().relative_to(root.resolve()).as_posix()


_PARSED: dict[tuple, tuple] = {}


def _parse(p: Path):
    """(text, tree) of a Python file, parsed once per process and version of
    the file; (None, None) when it cannot be read as UTF-8 or parsed."""
    try:
        st = p.stat()
    except OSError:
        return None, None
    key = (str(p.resolve()), st.st_mtime_ns, st.st_size)
    if key not in _PARSED:
        try:
            text = p.read_text(encoding="utf-8")
            _PARSED[key] = (text, ast.parse(text))
        except (UnicodeDecodeError, SyntaxError, ValueError, OSError):
            _PARSED[key] = (None, None)
    return _PARSED[key]


def _module_constants(path: Path) -> dict[str, object]:
    """Module-level literals and Path expressions, evaluated without import."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
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
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
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
    default = derive_cli_default(ast.parse((root / CLI_API).read_text(encoding="utf-8")), prompts)
    live = sorted({current, default})
    tuned = "tuned" in prompts
    return {"prompts": prompts, "current": current, "default": default, "live": live,
            "tuned_prompt": _required(env, "TUNED_PROMPT", str) if tuned else None,
            "components": _required(env, "COMPONENTS", str) if tuned else None,
            "receipt_conditions": sorted(_required(env, "RECEIPT_CONDITIONS", tuple)),
            "phases": list(_required(env, "PHASES", tuple, nonempty=True)),
            "derived_phases": sorted(_required(env, "DERIVED_PHASES", tuple)),
            "core_derived": _required(env, "CORE_DERIVED", bool),
            "agentic_runtimes": sorted(_required(env, "AGENTIC_RUNTIMES", tuple, nonempty=True))}


# --------------------------------------------------------------------------
# discovery from the code (#4023)


def _is_test(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    return (any(part in {"tests", "test"} for part in parts[:-1]) or name.startswith("test_")
            or name.endswith("_test.py") or name == "conftest.py")


def _python_sources(root: Path, tops=("src", "notes", "scripts")) -> tuple[list[Path], int]:
    """Every non-test Python file under the trees code runs from, minus
    registered byte copies (frozen run evidence) and hidden directories, and
    how many registered copies were skipped."""
    out, skipped = [], 0
    for top in tops:
        for p in sorted((root / top).rglob("*.py")):
            rel = _rel(root, p)
            if _is_test(rel) or "/." in "/" + rel:
                continue
            if REGISTERED_COPY.search(rel):
                skipped += 1
                continue
            out.append(p.resolve())         # resolved: import resolution compares resolved paths
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


_TARGETS: dict[tuple, tuple] = {}


def _local_import_targets(root: Path, p: Path, tree, index: dict[str, list[Path]]) -> list[Path]:
    """Modules under notes/ a module imports: relative imports; absolute
    imports resolved through its own directory or an ancestor below notes/
    (the controllers put the experiment directory on sys.path); and, failing
    both, the one notes/ module of that name when exactly one exists (a
    controller that puts another experiment directory on sys.path). Memoized
    per (module, tree, index): the driver search asks for every module on
    every pass."""
    key = (str(root), str(p))
    entry = _TARGETS.get(key)
    if entry is not None and entry[0] is tree and entry[1] is index:
        return entry[2]
    targets = _resolve_local_imports(root, p, tree, index)
    _TARGETS[key] = (tree, index, targets)
    return targets


def _resolve_local_imports(root: Path, p: Path, tree, index: dict[str, list[Path]]) -> list[Path]:
    notes = (root / "notes").resolve()
    here = p.resolve().parent
    dirs = [d for d in [here, *here.parents] if d == notes or notes in d.parents]

    def resolve(base: Path, dotted: str) -> list[Path]:
        q = base.joinpath(*dotted.split(".")) if dotted else base
        if _exists_exact(q.with_suffix(".py")) and q.with_suffix(".py").is_file():
            return [q.with_suffix(".py")]
        if dotted and (q / "__init__.py").is_file() and _exists_exact(q):
            return [q / "__init__.py"]
        return []

    found: list[Path] = []
    for node in _summary(tree)["imports"]:
        if isinstance(node, ast.ImportFrom) and node.level:
            base = here
            for _ in range(node.level - 1):
                base = base.parent
            mod = node.module or ""
            found += resolve(base, mod)
            found += [t for a in node.names for t in resolve(base, f"{mod}.{a.name}".strip("."))]
        else:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                if not name or name.split(".")[0] in {"data_sheets_schema", "src"}:
                    continue
                hit = next((r for d in dirs if (r := resolve(d, name))), [])
                if not hit and len(index.get(name.split(".")[0], [])) == 1:
                    only = index[name.split(".")[0]][0]
                    hit = resolve(only.parent.parent if only.name == "__init__.py" else only.parent, name)
                found += hit
    return [f.resolve() for f in found if f.resolve() != p.resolve()]


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


def _candidate_controller(root: Path, p: Path) -> bool:
    """A notes/ module that may seed or run a generation controller: not a
    diagnostic probe and not an evaluator (its path says which)."""
    rel = _rel(root, p)
    return rel.startswith("notes/") and "probe" not in p.stem and not EVALUATION_PATH.search(rel)


def run_controllers(root: Path, parsed: dict, index: dict) -> tuple[dict[str, Path], dict[str, str], set[Path]]:
    """Generation controllers under notes/, derived from what they do rather
    than a glob list (#4023). A seed builds or renders a generation request
    (uses RunSpec, build_phase, prompt_body, ...); the controller set is the
    seeds, every notes/ module they import, and every module that runs one
    (imports one, or stages one by file name), to a fixed point. The import
    closure stops at an evaluation module (a shared sequence ledger imports
    one for evaluation sequences): those are returned apart and never gate."""
    why: dict[str, str] = {}
    for p, (_, tree) in parsed.items():
        used = _builders_used(tree) if _candidate_controller(root, p) else []
        if used:
            why[_rel(root, p)] = "builds a generation request (" + ", ".join(used) + ")"
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
            todo += [(p.parent / lit).resolve() for lit in _str_constants(tree)
                     if re.fullmatch(r"[\w.-]+\.py", lit) and (p.parent / lit).resolve() in parsed]

    close([p for p in parsed if _rel(root, p) in why])
    while True:
        names = {(p.parent, p.name) for p in controllers.values()}
        resolved = {p.resolve(): rel for rel, p in controllers.items()}
        drivers = []
        for p, (_, tree) in sorted(parsed.items()):
            rel = _rel(root, p)
            if rel in controllers or not _candidate_controller(root, p):
                continue
            imported = sorted({resolved[t.resolve()] for t in _local_import_targets(root, p, tree, index)
                               if t.resolve() in resolved})
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
    resolved = {p.resolve() for p in controllers.values()}
    out: dict[str, str] = {}
    todo = []
    for p in sorted(reached):
        out[_rel(root, p)] = "evaluation module a run controller imports (an evaluation-sequence branch)"
        todo.append(p)
    for p, (_, tree) in sorted(parsed.items()):
        rel = _rel(root, p)
        if rel.startswith("notes/") and EVALUATION_PATH.search(rel) and rel not in controllers and \
                rel not in out and any(t.resolve() in resolved for t in _local_import_targets(root, p, tree, index)):
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


def discover(root: Path) -> tuple[Surfaces, dict]:
    s = Surfaces()
    facts: dict = {}
    src = root / "src/data_sheets_schema"
    prompts_dir = root / "src/download/prompts"

    # ---- api: runner closure, conditions, evidence protocols
    api_closure = _package_closure(root, ["data_sheets_schema.cli.api", "data_sheets_schema.api_runner"])
    facts["api_closure"] = [_rel(root, p) for p in api_closure]
    for p in api_closure:
        stem = p.stem if p.name != "__init__.py" else p.parent.name
        role = "model_facing" if stem in MODEL_FACING_MODULES else "run_shaping"
        s.add(_rel(root, p), "api", role, "live", "import closure of cli/api.py + api_runner")
    cond = condition_table(root)
    facts["conditions"] = cond
    for name, rel in sorted(cond["prompts"].items()):
        status = "live" if name in cond["live"] else "historical"
        s.add(rel, "api", "model_facing", status, f"condition prompt `{name}`")
    if cond["tuned_prompt"]:
        s.add(cond["tuned_prompt"], "api", "model_facing", "historical", "condition `tuned` base")
    if cond["components"]:
        for p in sorted((root / cond["components"]).glob("*.md")):
            if p.name.lower() == "readme.md":
                s.add(_rel(root, p), "api", "run_shaping", "historical", "components README")
            else:
                s.add(_rel(root, p), "api", "model_facing", "historical", "condition `tuned` component")
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

    # ---- every non-test Python module, parsed once (#4023)
    sources, skipped = _python_sources(root)
    facts["python_sources"] = [_rel(root, p) for p in sources]
    facts["registered_copies_skipped"] = skipped
    parsed = {}
    for p in sources:
        text, tree = _parse(p)
        if tree is not None:
            parsed[p] = (text, tree)
    facts["unparsed_python"] = sorted(_rel(root, p) for p in sources if p not in parsed)
    index = _notes_index(root, parsed)

    # ---- run controllers under notes/ (#4023): what they do, not a glob
    controllers, controller_why, evaluation_reached = run_controllers(root, parsed, index)
    facts["controllers"] = controller_why
    for rel in controller_why:
        s.add(rel, "run_controllers", "run_shaping", "live", "run controller: " + controller_why[rel])
    controller_text = {}
    for rel, p in sorted(controllers.items()):
        for name in _md_literals(parsed[p][1]):
            md = p.parent / name
            if md.is_file():
                controller_text.setdefault(_rel(root, md), rel)
    facts["controller_text"] = controller_text
    for rel, by in sorted(controller_text.items()):
        s.add(rel, "run_controllers", "model_facing", "live", f"text a controller hands to the model ({by})")

    # ---- native agentic: every playbook and agent that a playbook, a live
    # prompt, a run controller or the assistant instructions name, by path,
    # bare name or slash command, followed through the files they name
    commands = sorted((root / ".claude/commands").glob("*.md"))
    agents = sorted((root / ".claude/agents").glob("*.md"))
    claude_names = {p.stem: _rel(root, p) for p in commands + agents if p.stem.lower() != "readme"}
    referenced: set[str] = set()
    todo = [c for c in commands if c.name.startswith("d4d-")]
    todo += [root / cond["prompts"][c] for c in cond["live"]]
    todo += [root / rel for rel in controller_text]
    todo += sorted((root / ".github/workflows").glob("d4d_assistant_*.md"))
    for p in controllers.values():          # a controller names files in its literals, not its comments
        for ref in _named_claude_files("\n".join(_str_constants(parsed[p][1])), claude_names):
            if ref not in referenced:
                referenced.add(ref)
                todo.append(root / ref)
    visited: set[Path] = set()
    while todo:
        p = todo.pop()
        if p in visited or not p.is_file():
            continue
        visited.add(p)
        for ref in _named_claude_files(p.read_text(encoding="utf-8"), claude_names):
            if ref not in referenced:
                referenced.add(ref)
                todo.append(root / ref)
    facts["native_referenced"] = sorted(referenced)
    for p in commands:
        rel = _rel(root, p)
        if p.name.startswith("d4d-"):
            s.add(rel, "native_agentic", "model_facing", "live", "d4d playbook (slash command)")
        elif rel in referenced:
            s.add(rel, "native_agentic", "model_facing", "live",
                  "command named by a playbook, live prompt, controller or the assistant instructions")
    for p in agents:
        rel = _rel(root, p)
        if rel in referenced:
            s.add(rel, "native_agentic", "model_facing", "live",
                  "agent named (path, bare name or slash command) by a playbook, live prompt, controller "
                  "or the assistant instructions")
        else:
            s.add(rel, "native_agentic", "exposed", "live",
                  "handed to native runs by agentic_runtime.toolchain(); no playbook, live prompt, controller "
                  "or assistant instruction names it")
    playbook = root / ".claude/commands/d4d-full-core.md"
    groups = sorted(set(re.findall(r"\bd4d ([a-z][\w-]*) [a-z]", playbook.read_text(encoding="utf-8"))))
    starts = ["data_sheets_schema.agentic_runtime"] + [
        f"data_sheets_schema.cli.{g.replace('-', '_')}" for g in groups
        if (src / "cli" / f"{g.replace('-', '_')}.py").exists()]
    # the package modules the controllers import (the native audit batch, renderer >= 20)
    for p in controllers.values():
        for node in ast.walk(parsed[p][1]):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("data_sheets_schema"):
                starts += [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                starts += [a.name for a in node.names if a.name.startswith("data_sheets_schema")]
    facts["native_cli_groups"] = groups
    native_closure = _package_closure(root, sorted(set(starts)))
    facts["native_closure"] = [_rel(root, p) for p in native_closure]
    for p in native_closure:
        stem = p.stem if p.name != "__init__.py" else p.parent.name
        role = "model_facing" if stem in MODEL_FACING_MODULES else "run_shaping"
        s.add(_rel(root, p), "native_agentic", role, "live",
              "closure of agentic_runtime, the playbook's CLI groups and the controllers' imports")
    for p in sorted((root / ".claude/agents/scripts").glob("*.py")):
        s.add(_rel(root, p), "native_agentic", "run_shaping", "live", "agent helper script")

    # ---- every module that calls a model client (#4023), wherever it is
    in_closure = set(facts["api_closure"]) | set(facts["native_closure"]) | set(controllers)
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
            where = "the api/native import closure"
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

    # ---- github assistant
    wf = root / ".github/workflows"
    for p in sorted(wf.glob("d4d_assistant_*.md")):
        s.add(_rel(root, p), "github_assistant", "model_facing", "live",
              "assistant instruction file (loaded by /d4d-assistant and /d4d-webfetch)")
    for p in sorted(wf.glob("d4d-agent.yml")) + sorted(wf.glob("d4d_assistant_*.config")):
        s.add(_rel(root, p), "github_assistant", "run_shaping", "live", "assistant workflow / config")
    if cond["default"] in cond["prompts"]:
        s.add(cond["prompts"][cond["default"]], "github_assistant", "model_facing", "live",
              "condition the workflow runs (no --condition: the CLI default)")

    # ---- shared schema
    schema_dir = src / "schema"
    roots = ("data_sheets_schema.yaml", "data_sheets_schema_core.yaml")
    closure = sorted({p for r in roots for p in _schema_closure(schema_dir, r)})
    facts["schema_closure"] = [_rel(root, p) for p in closure]
    for p in closure:
        s.add(_rel(root, p), "shared_schema", "model_facing", "live", "generation schema import closure")
    native_schemas = _module_constants(src / "agentic_runtime.py").get("SCHEMAS") or ()
    for rel in native_schemas:
        s.add(rel, "shared_schema", "model_facing", "live", "merged schema the native playbook reads whole")
    for rel, role, why in (
            ("src/data_sheets_schema/profiles.py", "run_shaping", "profile selection"),
            ("src/data_sheets_schema/registry.py", "run_shaping", "manifest as project registry"),
            ("src/data_sheets_schema/b2ai_registry_vocabularies.yaml", "model_facing",
             "vocabulary pin rendered into the digest under the bridge2ai profile"),
            ("data/preprocessed/source_manifest.yaml", "model_facing",
             "study manifest: ranking, naming and scope blocks are rendered from it")):
        if (root / rel).exists():
            s.add(rel, "shared_schema", role, "live", why)

    # ---- deterministic arms
    for rel, role in (("src/data_sheets_schema/healthsheet.py", "model_facing"),
                      ("src/data_sheets_schema/rocrate_normalize.py", "model_facing"),
                      ("src/data_sheets_schema/rocrate_map.py", "run_shaping"),
                      ("src/data_sheets_schema/cli/healthsheet.py", "run_shaping"),
                      ("src/data_sheets_schema/cli/rocrate.py", "run_shaping")):
        if (root / rel).exists():
            s.add(rel, "deterministic", role, "live",
                  "builds a bundle a model reads" if role == "model_facing" else "deterministic arm")

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
    for sub in ("claude", "claudecode", "gpt5", "shared"):
        for p in sorted((prompts_dir / sub).rglob("*")):
            if p.is_file() and p.suffix in TEXT_SUFFIXES:
                if p.name.lower() == "readme.md":
                    s.add(_rel(root, p), "legacy_monolithic", "run_shaping", "legacy", "prompt-set README")
                else:
                    s.add(_rel(root, p), "legacy_monolithic", "model_facing", "legacy",
                          f"legacy prompt set ({sub})")

    # ---- upstream input (listed, never gates)
    for name in ("preprocess_sources.py", "concatenate_documents.py", "organized_dataset_extractor.py",
                 "enhanced_organized_extractor.py", "dataset_extractor.py"):
        p = root / "src/download" / name
        if p.exists():
            s.add(_rel(root, p), "shared_input", "run_shaping", "live", "input acquisition / bundle shaping")
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


def _model_text_ranges(text: str) -> list[tuple[int, int, str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    return [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and MODEL_TEXT_FUNCTION.match(n.name)]


def scan_file(root: Path, surface: Surface, tokens: list[Token]) -> list[dict]:
    """Every token hit in one surface. A file that cannot be read raises:
    the caller decides, and `run` refuses to report on a surface it could
    not see."""
    path = root / surface.path
    text = path.read_text(encoding="utf-8")
    # In a run controller, the string literals of a function that renders
    # what a model receives (render_instruction, render_system, ...) are
    # model-facing text even though the module as a whole shapes the run.
    ranges = (_model_text_ranges(text) if path.suffix == ".py" and surface.role == "run_shaping"
              and "run_controllers" in surface.approaches else [])
    hits = []
    for line, context, unit, src in units_for(path, surface.path, text):
        function = next((name for a, b, name in ranges if a <= line <= b), None) \
            if context == "string_literal" else None
        for _, _, tok, matched in match_text(unit, tokens):
            model_facing = context in MODEL_FACING_CONTEXTS and (surface.role == "model_facing"
                                                                 or function is not None)
            hit = {
                "path": surface.path, "line": line, "approaches": list(surface.approaches),
                "role": surface.role, "status": surface.status, "context": context,
                "category": tok.category, "match": matched, "pattern": tok.pattern,
                "model_facing": model_facing, "code": context in CODE_CONTEXTS,
                "snippet": src.strip()[:180],
            }
            if function is not None:
                hit["model_text_function"] = function
            hits.append(hit)
    return hits


GENERATION_NAMES = re.compile(r"\b(build_phase|resolve_prompt|RunSpec|digest_text|render_prompt|"
                              r"playbook_text|prompt_body|phase_instruction)\b")


def scan_tests(root: Path, tokens: list[Token]) -> list[dict]:
    """gc_project literals asserted on by a test that exercises generation."""
    out = []
    gc = [t for t in tokens if t.category == "gc_project"]
    for p in sorted((root / "tests").rglob("test_*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not GENERATION_NAMES.search(text):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
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
    return out


def is_violation(hit: dict) -> bool:
    gates = any(APPROACHES[a][0] for a in hit["approaches"])
    return (hit["category"] == "gc_project" and hit.get("exception") is None and gates
            and (hit["model_facing"] or hit["code"]))


# --------------------------------------------------------------------------
# self-test: a scanner that sees nothing cannot pass


#: What the self-test plants. Every planted item is checked for its context
#: (Python) or category (Markdown) AND the line it was planted on (#4026):
#: an implicitly concatenated literal whose token sits on its second line, a
#: triple-quoted block, and the table forms #4024 added (a frozenset
#: constant, a lookup default, a keyword argument, a loop tuple).
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
                "    pass\n"),                                   # 17
}
SELF_TEST_EXPECT = {
    "seed.md": {("gc_project", "AI-READI", 3), ("bridge2ai_program", "Bridge2AI", 4),
                ("biomedical_clinical", "clinical", 5)},
    "seed.py": {("code_branch", "CHORUS", 2), ("string_literal", "fairhub", 3), ("comment", "VOICE", 4),
                ("code_table", "CM4AI", 5), ("string_literal", "physionet", 7),
                ("code_table", "AI_READI", 8), ("code_table", "VOICE_PEDIATRIC", 10),
                ("string_literal", "voicepeds", 13), ("code_table", "aireadi", 15),
                ("code_table", "dataverse", 16)},
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
# "api" meaning, derived from the code (#4022, #4025)


def _function(tree: ast.Module, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def shape_of(model_phases: list, followups: dict) -> str:
    """MONOLITHIC only for one model phase and no follow-up turn."""
    return "MULTI-PHASE" if (len(model_phases) > 1 or followups) else "MONOLITHIC"


def _int_values(node) -> list[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _int_values(node.body) + _int_values(node.orelse)
    return []


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


def _renderer_setters(tree: ast.Module, floor: int) -> list[dict]:
    """Where a module sets a renderer >= floor: a `render_version=` keyword,
    a `["render_version"] =` / `.render_version =` assignment, or a
    `"render_version":` dict entry."""
    out = []

    def keep(node, values):
        values = [v for v in values if v >= floor]
        if values:
            out.append({"line": node.lineno, "renderers": sorted(set(values))})

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "render_version":
            keep(node.value, _int_values(node.value))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                key = t.slice.value if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) \
                    else _attr_or_name(t)
                if key == "render_version" and node.value is not None:
                    keep(node, _int_values(node.value))
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "render_version":
                    keep(v, _int_values(v))
    return out


def _agentic_parent_gates(tree: ast.Module) -> list[dict]:
    """`if (spec.condition != "X" or spec.render_version != N or not
    spec.is_agentic ...): raise`: a continuation that refuses any parent
    that is not an agentic run (of condition X at renderer N, when named)."""
    gates = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and any(isinstance(b, ast.Raise) for b in node.body)):
            continue
        test = node.test
        if not any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not)
                   and _attr_or_name(n.operand) == "is_agentic" for n in ast.walk(test)):
            continue
        gate = {"line": node.lineno, "condition": None, "parent_renderer": None}
        for left, op, right in _compares(test):
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


def audit_continuations(root: Path, floor: int, sources: list[str], runner_tree: ast.Module) -> dict:
    """Which runs reach the renderer from which the audit is a native batch
    (#4022). Every module that sets a renderer >= floor is found; it is a
    native continuation when its controller package (its directory) holds a
    gate that refuses any parent that is not an agentic run. A continuation
    without such a gate could continue an API run, which would make that run
    an API + native hybrid. An API run that itself reaches the floor is not
    a hybrid: `build_phase` refuses its audit, so it stops there."""
    setters, gates_by_dir = [], {}
    for rel in sources:
        p = root / rel
        text, tree = _parse(p)
        if tree is None:
            continue
        # a setter names render_version and a gate names is_agentic: a module
        # whose source names neither cannot hold one, so its tree is not walked
        if "render_version" in text:
            setters += [{"path": rel, **x} for x in _renderer_setters(tree, floor)]
        if "is_agentic" in text:
            for g in _agentic_parent_gates(tree):
                gates_by_dir.setdefault(p.resolve().parent, []).append({"path": rel, **g})
    used: dict[str, dict] = {}
    for x in setters:
        gates = gates_by_dir.get((root / x["path"]).resolve().parent, [])
        x["gates"] = sorted(f"{g['path']}:{g['line']}" for g in gates)
        used.update({f"{g['path']}:{g['line']}": g for g in gates})
    uncovered = [x for x in setters if not x["gates"]]
    cli_inputs = _renderer_inputs(ast.parse((root / CLI_API).read_text(encoding="utf-8")))
    defaults = derive_default_renderer(runner_tree)
    gate_text = "; ".join(f"{k} refuses a parent that is not an agentic run"
                          + (f" of {g['condition']}" if g["condition"] else "")
                          + (f" at renderer {g['parent_renderer']}" if g["parent_renderer"] is not None else "")
                          for k, g in sorted(used.items()))
    setter_text = ", ".join(sorted({f"{x['path']}:{x['line']}" for x in setters}))
    if uncovered:
        why = (f"renderer >= {floor} is set with no agentic-parent gate in its controller package at "
               + ", ".join(f"{x['path']}:{x['line']}" for x in uncovered)
               + ", so a native audit continuation of an API run cannot be ruled out")
    elif setters:
        why = (f"renderer >= {floor} is set only by native audit continuations ({setter_text}), and each sits "
               f"in a controller package that refuses its parent unless it is a native run ({gate_text}): the "
               "native audit batch continues native generations only")
    else:
        why = f"no module sets renderer >= {floor}"
    api_path = (f"`d4d api` can hand RunSpec a renderer ({'; '.join(cli_inputs)})" if cli_inputs else
                f"`d4d api` hands RunSpec no renderer (the API default is {defaults['api']})")
    if defaults["api"] >= floor:
        api_path += f"; the API default renderer {defaults['api']} is at or above {floor}"
    api_path += (f"; and `build_phase` refuses the audit phase at renderer >= {floor} on any spec, so an API run "
                 "that reached it would stop at audit, not become a hybrid")
    return {"floor": floor, "setters": setters, "gates": [{"at": k, **g} for k, g in sorted(used.items())],
            "uncovered": [f"{x['path']}:{x['line']}" for x in uncovered],
            "api_cli_renderer_inputs": cli_inputs, "default_renderer": defaults,
            "api_reaches_floor": bool(cli_inputs) or defaults["api"] >= floor,
            "runtime_hybrid_possible": bool(uncovered), "why": why, "api_path": api_path}


def api_meaning(root: Path, facts: dict) -> dict:
    for key in ("conditions", "python_sources", "legacy_scripts"):
        if key not in facts:
            raise ConfigError(f"api_meaning needs discover()'s facts; `{key}` is missing")
    runner_text = (root / RUNNER).read_text(encoding="utf-8")
    tree = ast.parse(runner_text)
    cond = facts["conditions"]
    phases = cond["phases"]
    derived = cond["derived_phases"] if cond["core_derived"] else []
    model_phases = [p for p in phases if p not in derived]

    build = _function(tree, "build_phase")
    if build is None:
        raise _not_derived("the phase builder", "api_runner.py defines no build_phase")
    calls = {n.attr for n in ast.walk(build) if isinstance(n, ast.Attribute)} | \
        {n.id for n in ast.walk(build) if isinstance(n, ast.Name)}
    consts = [n.value for n in ast.walk(build) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    if "digest_text" in calls:
        schema_form = "schema digest (schema_digest.digest_text)"
    elif any("_all.yaml" in c for c in consts):
        schema_form = "merged LinkML schema (_all.yaml)"
    else:
        raise _not_derived("the schema form a phase sends", "build_phase names neither digest_text nor _all.yaml")
    whole_schema = schema_form.startswith("schema digest") and any("_all.yaml" in c for c in consts)
    floor = derive_agentic_audit_from(build)
    continuation = audit_continuations(root, floor, facts["python_sources"], tree)
    funcs = sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef))
    instruction_keys = None
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name) and target.id == "PHASE_INSTRUCTIONS" and \
                    isinstance(node.value, ast.Dict):
                instruction_keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
    if instruction_keys is None:
        raise _not_derived("the follow-up turns", "api_runner.PHASE_INSTRUCTIONS is not a module-level dict")
    # A follow-up turn is an instruction the runner can send that is not one
    # of the PHASES, or a builder for one (build_readdress, build_repair).
    followups: dict[str, list[str]] = {}
    for key in instruction_keys:
        if key not in phases and key != "full_receipt":
            followups.setdefault(key, []).append("PHASE_INSTRUCTIONS")
    for f in funcs:
        if f.startswith("build_") and f != "build_phase":
            followups.setdefault(f[len("build_"):], []).append(f)

    claude_names = {p.stem: _rel(root, p) for d in (".claude/commands", ".claude/agents")
                    for p in sorted((root / d).glob("*.md")) if p.stem.lower() != "readme"}
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
        conditions[name] = {
            "status": "live" if name in cond["live"] else "historical",
            "role": ("current generic" if name == cond["current"] else "")
                    + (" + CLI default (GitHub assistant)" if name == cond["default"] else "")
                    + ("per-project tuning: appends components/{PROJECT}.md" if name == "tuned" else ""),
            "prompt": rel,
            "receipt_condition": name in cond["receipt_conditions"],
            "tuned": name == "tuned",
            "shape": shape_of(model_phases, followups),
            "model_calls_minimum": len(model_phases),
            "schema_form": schema_form + (" + merged-schema reference" if whole_schema else ""),
            "prompt_hybrid": bool(refs),
            "runtime_hybrid": continuation["runtime_hybrid_possible"],
            "hybrid_reasons": hybrid,
            "prompt_body_references": refs,
            "appends": ([cond["tuned_prompt"], f"{cond['components']}/{{PROJECT}}.md"]
                        if name == "tuned" else []),
        }

    arms_table = _module_constants(root / CLI_API).get("ARMS")
    if not isinstance(arms_table, dict) or not arms_table:
        raise _not_derived("the API arms", "cli/api.py ARMS is not a module-level dict literal")
    arms = {}
    for arm, row in sorted(arms_table.items()):
        arms[arm] = {"method_dir": row[1], "bundle": row[2],
                     "shape": "MULTI-PHASE (same phase list as every condition)",
                     "manifest": row[3].replace("# Source manifest: ", "")}

    legacy = {}
    for rel in facts["legacy_scripts"]:
        text, ltree = _parse(root / rel)
        if ltree is None:
            legacy[rel] = {"shape": "UNPARSED", "model_call_sites": None, "full_schema": None,
                           "concatenated_input": None, "tool_decorators": None}
            continue
        n_calls = len(model_call_sites(ltree))
        full_schema = bool(re.search(r"_all\.yaml|get_full_schema", text))
        # concatenated input: the file name says so, or it reads the
        # concatenated bundles / the d4d_concatenated prompts (#4023)
        concatenated = "concatenat" in Path(rel).name or bool(
            re.search(r"preprocessed/concatenated|d4d_concatenated_\w*prompt", text))
        tools = re.findall(r"@[\w.]*\.tool(?:_plain)?\b", text)
        shape = ("MONOLITHIC" if n_calls == 1 and full_schema and concatenated and not tools else
                 "MONOLITHIC + TOOLS (hybrid)" if n_calls and full_schema and concatenated else
                 "PER-DOCUMENT" if n_calls and not concatenated else
                 "NO MODEL CALL" if not n_calls else "UNCLEAR")
        legacy[rel] = {"shape": shape, "model_call_sites": n_calls, "full_schema": full_schema,
                       "concatenated_input": concatenated, "tool_decorators": len(tools)}

    gh = {}
    yml = root / ".github/workflows/d4d-agent.yml"
    if yml.exists():
        text = yml.read_text(encoding="utf-8")
        m = re.search(r"d4d api run(?:[^\n]*\\\n)*[^\n]*", text)
        if m is None:
            raise _not_derived("what the GitHub assistant runs", "d4d-agent.yml has no `d4d api run` command")
        block = m.group(0)
        cm = re.search(r"--condition\s+(\S+)", block)
        ran = cm.group(1) if cm else cond["default"]
        gh = {"command": " ".join(block.replace("\\\n", " ").split()),
              "condition": cm.group(1) if cm else f"{cond['default']} (CLI default; no --condition)",
              "manifest": "given" if "--manifest" in block else "none passed (neutral for an external bundle)",
              "shape": conditions[ran]["shape"] if ran in conditions else "unknown condition"}

    playbook = (root / ".claude/commands/d4d-full-core.md").read_text(encoding="utf-8")
    native = {"playbook": ".claude/commands/d4d-full-core.md",
              "phases": re.findall(r"(?m)^#+\s*(Phase \d+[^\n]*)", playbook)[:8],
              "schema_form": "merged LinkML schema files read whole (agentic_runtime.SCHEMAS)",
              "shape": "AGENTIC MULTI-PHASE"}

    live_shapes = {c: conditions[c]["shape"] for c in cond["live"]}
    mono_legacy = sorted(k for k, v in legacy.items() if v["shape"] == "MONOLITHIC")
    verdict = []
    if all(v == "MULTI-PHASE" for v in live_shapes.values()):
        verdict.append(f"No live API condition ({', '.join(cond['live'])}) is monolithic: each run makes at "
                       f"least {len(model_phases)} model calls ({', '.join(model_phases)}), sends the "
                       f"{schema_form} rather than the LinkML schema, and may add follow-up turns "
                       f"({', '.join(sorted(followups))}).")
    else:
        verdict.append("Live API conditions that are MONOLITHIC: "
                       + ", ".join(c for c, v in live_shapes.items() if v == "MONOLITHIC") + ".")
    if mono_legacy:
        verdict.append("The monolithic shape (prompt + full LinkML schema + concatenated documents, one call) "
                       f"survives only in {len(mono_legacy)} scripts outside the runner: "
                       + ", ".join(mono_legacy) + ".")
    else:
        verdict.append("No script outside the runner has the monolithic shape.")
    prompt_hybrids = sorted(c for c in cond["live"] if conditions[c]["prompt_hybrid"])
    if prompt_hybrids:
        verdict.append("Prompt-level hybrid: the live conditions " + ", ".join(prompt_hybrids) + " tell the "
                       "API model to read playbook files the API request never carries ("
                       + ", ".join(sorted({r for c in prompt_hybrids for r in conditions[c]["prompt_body_references"]}))
                       + ").")
    if continuation["runtime_hybrid_possible"]:
        verdict.append("A runtime hybrid (an API run whose audit is a native batch) cannot be ruled out: "
                       + continuation["why"] + ".")
    else:
        verdict.append("No API condition is a runtime hybrid: " + continuation["why"] + "; "
                       + continuation["api_path"] + ".")
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
            "github_assistant": gh, "native": native, "verdict": verdict}


# --------------------------------------------------------------------------
# report


def _git_head(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run(root: Path, tokens_file: Path = TOKENS_FILE, exceptions_file: Path = EXCEPTIONS_FILE) -> dict:
    tokens = load_tokens(root, tokens_file)
    st = self_test(tokens)
    if not st["passed"]:
        return {"self_test": st, "exit": 2}
    exceptions = load_exceptions(exceptions_file)
    surfaces, facts = discover(root)
    hits, unreadable = [], []
    for rel in sorted(surfaces.files):
        try:
            hits.extend(scan_file(root, surfaces.files[rel], tokens))
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{rel} ({type(exc).__name__})")
    if unreadable:
        raise ConfigError("discovered surfaces could not be read, so the scan cannot vouch for them: "
                          + "; ".join(unreadable))
    used = {}
    for h in hits:
        e = exception_for(h, exceptions)
        h["exception"] = None if e is None else e["_index"]
        if e is not None:
            used[e["_index"]] = used.get(e["_index"], 0) + 1
        h["violation"] = is_violation(h)
    tests = scan_tests(root, tokens)
    meaning = api_meaning(root, facts)
    violations = [h for h in hits if h["violation"]]
    return {"root": root.name, "commit": _git_head(root), "self_test": st,
            "surfaces": {k: vars(v) for k, v in sorted(surfaces.files.items())}, "facts": facts,
            "exceptions": [{k: v for k, v in e.items() if not k.startswith("_")} | {"index": e["_index"],
                           "hits": used.get(e["_index"], 0)} for e in exceptions],
            "hits": hits, "violations": violations, "test_dependencies": tests,
            "api_meaning": meaning, "exit": 1 if violations else 0}


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
    return out


def _table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return out


def _why_quiet(h: dict) -> str:
    if h["exception"] is not None:
        return f"exception #{h['exception']}"
    if h["role"] == "exposed":
        return "exposed"
    if not any(APPROACHES[a][0] for a in h["approaches"]):
        return "non-gating approach (" + ", ".join(h["approaches"]) + ")"
    return h["context"]


def render_markdown(result: dict) -> str:
    L = ["# D4D generation-specificity audit", ""]
    st = result["self_test"]
    L += [f"Checkout `{result.get('root')}` at commit `{result.get('commit')}`; generated by "
          f"`.claude/skills/d4d-generation-specificity-audit/scan.py`.",
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
        by = {r: sum(s["role"] == r for s in files) for r in ROLE_RANK}
        rows.append([a, "yes" if gates else "no", len(files), by["model_facing"], by["exposed"],
                     by["run_shaping"], desc])
    L += _table(rows, ["approach", "gates exit", "files", "model-facing", "exposed", "run-shaping",
                       "what"]) + [""]

    f = result["facts"]
    L += ["## How the surfaces were found", "",
          f"- Python modules read: {len(f['python_sources'])} non-test modules under `src/`, `notes/` and "
          f"`scripts/` ({f['registered_copies_skipped']} registered byte copies under `registrations/` skipped"
          + (f"; could not parse: {', '.join(f['unparsed_python'])}" if f["unparsed_python"] else "") + ").",
          f"- Run controllers: {len(f['controllers'])} modules under `notes/`. A seed builds a generation "
          "request; the rest are imported by a controller or run one (imports one, or stages its files by name).",
          "- Text a controller hands to the model: "
          + (", ".join(f"`{k}`" for k in f["controller_text"]) or "none") + ".",
          "- Playbooks and agents a playbook, a live prompt, a controller or the assistant instructions name "
          "(path, bare name or slash command): " + ", ".join(f"`{r}`" for r in f["native_referenced"]) + ".",
          ""]
    L += _table([[f"`{p}`", w] for p, w in f["controllers"].items()], ["run controller", "why"]) + [""]
    L += _table([[f"`{p}`", ", ".join(v["evidence"])[:120], v["classified"]] for p, v in f["model_clients"].items()],
                ["module that calls a model client", "evidence", "classified as"]) + [""]
    if f["evaluation_controllers"]:
        L += ["Evaluation controllers (listed under other_model_client, never gating): "
              + ", ".join(f"`{p}`" for p in f["evaluation_controllers"]) + ".", ""]

    L += ["## gc_project violations", "",
          "A Grand Challenge project's name, site or identifier in model-facing text or in a code "
          "branch/table of a generation surface, with no tracked exception. Fix each: move the fact "
          "into the manifest or profile, or remove it.", ""]
    if viol:
        L += _table([[f"`{h['path']}:{h['line']}`", ",".join(h["approaches"]), h["status"],
                      h["context"] + (f" in {h['model_text_function']}()" if h.get("model_text_function") else ""),
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
          "Excepted, in comments/docstrings/headers, in run-shaping literals, in files the native "
          "toolchain exposes but no playbook names, or in a non-gating approach (upstream input, "
          "other model clients).", ""]
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
    L.append("")

    L += ["## Exceptions", ""]
    L += _table([[e["index"], e["path"], e.get("token") or "", e.get("category") or "", e["hits"],
                  e["reason"][:140], e["decision"]] for e in result["exceptions"]],
                ["#", "path", "token", "category", "hits", "reason", "decision"]) + [""]
    unused = [e for e in result["exceptions"] if e["hits"] == 0]
    if unused:
        L += ["Unused exceptions (stale, or the finding was fixed): "
              + ", ".join(f"#{e['index']}" for e in unused), ""]

    m = result["api_meaning"]
    ac = m["audit_continuations"]
    L += ["## What \"api\" means in the code", "", f"Definition checked: {m['definition']}.", ""]
    L += [f"- Phases (`api_runner.PHASES`): {', '.join(m['phases'])}; derived without a model call: "
          f"{', '.join(m['derived_phases']) or 'none'}; model phases: {', '.join(m['model_phases'])}.",
          f"- Schema sent: {m['schema_form']}.",
          "- Follow-up turns: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in m["followup_turns"].items()),
          f"- Native audit batch: from renderer {m['agentic_audit_from_renderer']}, `build_phase` refuses the "
          f"audit phase on every spec and the audit is a registered native batch. Default renderer when none is "
          f"registered: {m['default_renderer']['api']} for the API runtime, {m['default_renderer']['agentic']} "
          f"for an agentic one.",
          f"- Who reaches renderer {ac['floor']} or above: {ac['why']}. {ac['api_path'][0].upper()}"
          f"{ac['api_path'][1:]}.",
          f"- Agentic runtimes that render the same condition names (one name, two procedures; not a hybrid "
          f"run): {', '.join(m['agentic_runtimes'])}.", ""]
    L += _table([[c, v["status"], v["role"].strip(" +") or "", v["shape"], v["model_calls_minimum"],
                  "yes" if v["receipt_condition"] else "", "yes" if v["prompt_hybrid"] else "no",
                  "possible" if v["runtime_hybrid"] else "no", ", ".join(v["prompt_body_references"])]
                 for c, v in m["conditions"].items()],
                ["condition", "status", "role", "shape", "min model calls", "receipt",
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
