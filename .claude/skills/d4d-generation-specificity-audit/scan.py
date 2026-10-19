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
    "offline_draft": (True, "explicit offline prompt-draft builders; inspected instruction text only, "
                            "not a registered live condition or evidence of model delivery"),
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

#: Modules whose text reaches a model (prompt assembly, bundle text, digest),
#: kept by hand as a cross-check of the derivation (#4085): whether a
#: top-level `data_sheets_schema` module writes model-facing text is derived
#: by data flow (`derive_model_facing`), and the report lists every module
#: the derivation finds that this list lacks, and every one it names that
#: the derivation does not reach. A module either names is model-facing, so
#: a gap in the derivation never stops a module here from gating in
#: silence. tests/test_generation_specificity_skill.py fails when a name here
#: is in none of the api, native or deterministic closures, and when this
#: checkout's derivation and this list disagree.
MODEL_FACING_MODULES = frozenset({
    "api_runner", "schema_digest", "schema_semantics", "source_review", "grounding",
    "scope", "source_priority", "source_metadata", "chunking", "evidence_assertions",
    "agentic_runtime", "audit_batch_context", "audit_batch_format", "audit_grammar",
    "healthsheet", "rocrate_normalize",
    "shared_generation", "typed_audit_runtime", "typed_audit", "audit_omissions", "audit_batches",
    "source_heading_runtime",
    # found by the derivation (#4085): the opt-in renderer-24 receipt turn,
    # the API playbook adaptation, the native attribution instructions, the
    # receipt-completion and removal-repair requests and what they carry
    "rereceipt", "api_playbook", "native_source_attribution", "receipt_completion", "receipts", "removals",
})

#: The native shared-protocol modules, whose sources live on the native branch
#: and not on main, so they are not listed above: a listed module the
#: derivation cannot reach fails the list cross-check (88f909562). They keep
#: the list's guarantee anyway: present in a checkout, each is model-facing
#: even when the derivation misses it (#5082).
NATIVE_SHARED_MODULES = frozenset({
    "native_shared_render", "native_shared_stage", "native_shared_receipts", "native_shared_contract",
})

# Offline draft text remains distinct from live request text. The compiler can
# also be a run-shaping dependency of the explicit captured routing adapter.
OFFLINE_DRAFT_MODULES = ("src/data_sheets_schema/source_heading_routing.py",)

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
#: Calls the scan cannot resolve to a function whose result carries their
#: positional arguments' text: a copy, a conversion or a serialization
#: (`list(cached)`, `str(x)`, `json.dumps(inventory)`,
#: `yaml.safe_dump(manifest)`), read by the callee's last name (#4085).
TEXT_CARRYING_CALLS = frozenset({"str", "repr", "list", "tuple", "sorted", "reversed", "copy", "deepcopy",
                                 "dumps", "dump", "safe_dump", "dedent", "indent", "fill"})
#: Methods whose result is what a file holds, not the path they are called
#: on (#4085): `resource_path(name).read_bytes()` sends the file's bytes, so
#: the path expression is followed as data, never as text.
FILE_READ_METHODS = frozenset({"read_text", "read_bytes", "read", "readline", "readlines", "open"})
#: The fields of the runner's request that carry text to the model: the
#: system prompt and the messages, whose head is the cached prefix
#: (`cached_blocks`). A request's `phase` names the call for accounting and
#: is not sent (#4085).
REQUEST_TEXT_FIELDS = ("system", "cached_blocks", "messages")
#: The tree a run reads its inputs from (the bundles, their chunk mappings,
#: the manifest); a run's records go under data/d4d_concatenated/ (#4085).
INPUT_TREE = "data/preprocessed/"
#: A templated input a playbook names under the input tree, and the file
#: name after the project: `data/preprocessed/chunks/{PROJECT}_chunks.yaml`
#: -> `_chunks.yaml` (#4085).
TEMPLATED_INPUT = re.compile(re.escape(INPUT_TREE) + r"[\w./-]*\{PROJECT\}([\w.-]*\.\w+)")

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


def _prose(node) -> bool:
    """A string literal or f-string whose literal text has whitespace and a
    letter or digit: a sentence a module writes, not a bare token (a key, an
    identifier, a file name), which gates as code in any role, nor a
    separator or a rule line (#4085)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
    elif isinstance(node, ast.JoinedStr):
        text = "".join(str(v.value) for v in node.values if isinstance(v, ast.Constant))
    else:
        return False
    return bool(re.search(r"\s", text) and re.search(r"[^\W_]", text))


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


def _module_role(p: Path, derived=frozenset()) -> str:
    """model_facing for a top-level module of the `data_sheets_schema`
    package whose text the data flow found reaching a model (`derived`,
    #4085) or that MODEL_FACING_MODULES names, matched by its place in the
    package and not its stem alone (`cli/healthsheet.py` is not
    `healthsheet.py`). A native shared module is model-facing as if listed
    (NATIVE_SHARED_MODULES)."""
    name = _package_module_name(p)
    listed = name in MODEL_FACING_MODULES or name in NATIVE_SHARED_MODULES
    return "model_facing" if listed or name in derived else "run_shaping"


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
    routed = _required(env, "SOURCE_HEADING_CONDITIONS", tuple) if "SOURCE_HEADING_CONDITIONS" in env else ()
    if any(name not in prompts for name in routed):
        raise _not_derived("selected routing conditions", "a declared condition lacks its prompt")
    live = sorted({current, default, *routed})
    tuned = "tuned" in prompts
    reads = None
    if tuned:
        reads = derive_tuned_reads(_tree(root / RUNNER), env)
        reads["sends_tuned_prompt"] = "TUNED_PROMPT" in reads["reads"]
        reads["sends_components"] = "COMPONENTS" in reads["reads"]
    return {"prompts": prompts, "current": current, "default": default, "live": live,
            **({"registered_routing_conditions": list(routed)} if routed else {}),
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
            if (target, name) not in binds.values() and (target, None) not in binds.values():
                continue
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
    `nonlocal`, a match capture. The function's own parameters are not
    counted here: `_holder_shown` refuses a name holder that is one
    (#4166), while the name that holds an attribute or item may be one
    (`self`)."""
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


def _block_of(stmt, parents: dict) -> list:
    """The statement list that holds `stmt`, by identity: its function's
    body, or an `if`, loop, `try`, `except`, `with` or `match` body or
    branch."""
    owner = parents[id(stmt)]
    return next(v for _, v in ast.iter_fields(owner) if isinstance(v, list) and any(s is stmt for s in v))


def _holder_shown(rel: str, parents: dict, assign) -> tuple[bool, list[str]]:
    """Whether the name, attribute or item a plain or annotated assignment
    binds an argv list to holds that list, unchanged, wherever its function
    hands it on (#4156, #4166). Shown only for one target, in a function,
    that is a name or an attribute or literal-key item of a name (`argv`,
    `self.argv`, `job['argv']`), where:

    - that assignment is the holder's one binding in the function, and
      every other occurrence of the name (nested functions and classes
      included) comes after it in the same statement list, inside a
      statement that follows it there at any depth. An occurrence before
      it, or outside the block (an `if`, loop, `try`, `with` or `match`
      body) that holds it, can see what the holder held before the binding
      ran or on a path where it never runs (#4166);
    - a name holder is not a parameter of the function, which holds the
      caller's list until the binding runs (#4166), and neither the name
      nor the name that holds an attribute or item is declared `global` or
      `nonlocal`;
    - every such occurrence hands the holder on whole (a direct argument
      of a call, a returned or yielded value) or only reads it (a
      comparison, an f-string). For an attribute or item, the name that
      holds it is held to the same rule.

    Anything else, a binding, a deletion, an occurrence the binding does
    not precede in its block, or a use of any other kind, is a reason it is
    not shown."""
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

    # what runs after the binding on every path through its block (#4166)
    block = _block_of(assign, parents)
    i = next(k for k, s in enumerate(block) if s is assign)
    before = {id(x) for s in block[:i + 1] for x in ast.walk(s)}
    after = {id(x) for s in block[i + 1:] for x in ast.walk(s)}
    problems, uses = [], []
    if part is None and base in _params(fn):
        problems.append(f"{at} `{base}` is a parameter of `{fn.name}()`, which holds the caller's list until "
                        "the binding runs")
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
        elif id(n) in before:
            problems.append(f"{rel}:{x.lineno} {what} is used before the binding at line {assign.lineno}")
        elif id(n) not in after:
            problems.append(f"{rel}:{x.lineno} {what} is used outside the block that holds the binding at line "
                            f"{assign.lineno}, which may not have run there")
        elif (h := _handed_on(x, parents)) is not None:
            uses.append(f"line {x.lineno}: {what.strip(',')} {h[0]}")
        elif _reads(x, parents):
            uses.append(f"line {x.lineno}: {what.strip(',')} read")
        else:
            problems.append(f"{rel}:{x.lineno} {what} is {_use(x, parents)}")
    if problems:
        return False, problems
    return True, [f"{at} the argv list is bound to `{held}` as it is, before every other use of it in its block, "
                  "and the function otherwise only hands it on whole or reads it ("
                  + ("; ".join(uses) or "no other use") + ")"]


def _argv_shown(rel: str, parents: dict, lst) -> tuple[bool, list[str]]:
    """Whether a launch's argv list literal is, unchanged, the list its
    function hands over (#4156): the call's argument itself, in a call
    nothing keeps the value of (`subprocess.run([...])`, `with
    Popen([...]) as p:`); returned or yielded as it is; or the whole value
    of a plain or annotated assignment to a holder that is not a parameter,
    that the assignment binds before every other use of it in the same
    statement list, and that its function never changes (`_holder_shown`,
    #4166). (True, how) or (False, why not)."""
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
    by a holder used any other way, by a parameter, or bound where it may
    not have run before a use: in an `if`, loop, `try`, `with` or `match`
    body the use does not share, or after the use (#4166). What the code
    the list is handed to does with it (a callee, a caller) is not read. A
    launch flag outside a list or tuple literal is a launch whose flags
    cannot be read. Returns one row per launch: its site, `carries` and
    `memory_off` (True, False or None) and the evidence or the reasons for
    each."""
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


_DEFS: dict[int, tuple] = {}


def _function_defs(tree) -> dict[str, ast.AST]:
    """name -> the first function so named in a module, at any depth; cached
    per tree (the entry holds the tree, so its id is not reused)."""
    entry = _DEFS.get(id(tree))
    if entry is not None and entry[0] is tree:
        return entry[1]
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(n.name, n)
    _DEFS[id(tree)] = (tree, out)
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


def _import_time_nodes(stmt):
    """Every node of a top-level statement that runs when its module is
    imported: all of it but the bodies of the functions and lambdas it
    defines (their decorators, defaults and annotations run)."""
    todo = [stmt]
    while todo:
        n = todo.pop()
        yield n
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            todo += [c for c in ast.iter_child_nodes(n) if not isinstance(c, ast.stmt)]
        elif isinstance(n, ast.Lambda):
            todo.append(n.args)
        else:
            todo += ast.iter_child_nodes(n)


def _constant_writes(tree, name: str) -> list[tuple[ast.AST, list[ast.AST]]]:
    """Every write of the module constant `name` at the top of its module,
    with the expressions whose values become part of it (#4156, #4166): a
    top-level assignment to it, plain (also unpacked or chained),
    annotated or augmented (`NAME += ...`), or to an item or attribute of
    it (`NAME[k] = v`), and its value; and every method call whose
    receiver holds it (`NAME.append(v)`, `NAME['k'].append(v)`,
    `NAME.setdefault('k', []).append(v)`), wherever it sits in a top-level
    statement's code that runs on import (alone, in an assignment's value,
    in another call's argument, in a condition, in a block's body), and the
    call's arguments. Any method may change the object it is called on, so
    none is taken for a read: `DEFAULT = NAME.setdefault('d', POLICY)`
    puts POLICY in NAME (#4166). Not read: an assignment to it inside a
    block (`if`, `try`) or a function, a method call on it in the body of a
    function or lambda, a function it is handed to (`register(NAME, v)`),
    and a write through another name bound to it or to part of it."""
    out = []
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and stmt.value is not None:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if any(_writes_name(t, name) for t in targets):
                out.append((stmt, [stmt.value]))
        for call in _import_time_nodes(stmt):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and any(
                    isinstance(x, ast.Name) and x.id == name for x in ast.walk(call.func.value)):
                out.append((call, [a.value if isinstance(a, ast.Starred) else a for a in call.args]
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


def _holder(target) -> str | None:
    """The name whose object an expression writes into: `parts` for
    `parts`, `d['k']`, `req.messages[0]['content']`."""
    while isinstance(target, (ast.Subscript, ast.Attribute)):
        target = target.value
    return target.id if isinstance(target, ast.Name) else None


_WRITES: dict[int, tuple] = {}


def _local_values(fn) -> dict[str, list[ast.AST]]:
    """What each local of a function is bound to: the value of every
    assignment to it (plain, unpacked, annotated or augmented), and the
    iterable of a `for` loop that binds it (#4085). A fresh dict."""
    out = {k: list(v) for k, v in _local_assignments(fn).items()}
    for n in ast.walk(fn):
        if isinstance(n, (ast.For, ast.AsyncFor)):
            for x in ast.walk(n.target):
                if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
                    out.setdefault(x.id, []).append(n.iter)
    return out


def _local_writes(fn) -> dict[str, list[ast.AST]]:
    """What becomes part of each local of a function, for the data flow
    (#4085): the value of every assignment to it (plain, unpacked, annotated
    or augmented), the iterable of a `for` loop that binds it, and, for a
    name the function binds that is not a parameter, the arguments of every
    method call on it and every value assigned to an item or attribute of
    it (`parts.append(x)`, `d['k'] = v`, `req.messages[0]['content']
    .extend(...)`): any method may change the object it is called on, as
    for a module constant (#4166). Cached per function node."""
    entry = _WRITES.get(id(fn))
    if entry is not None and entry[0] is fn:
        return entry[1]
    out = _local_values(fn)
    bound = set(out) - set(_params(fn))
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and _holder(n.func.value) in bound:
            out[_holder(n.func.value)] += ([a.value if isinstance(a, ast.Starred) else a for a in n.args]
                                           + [k.value for k in n.keywords])
        elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and n.value is not None:
            for t in n.targets if isinstance(n, ast.Assign) else [n.target]:
                if isinstance(t, (ast.Subscript, ast.Attribute)) and _holder(t) in bound:
                    out[_holder(t)].append(n.value)
    _WRITES[id(fn)] = (fn, out)
    return out


def _results(fn) -> list[ast.AST]:
    """What a function's result is built from: its returned values, and the
    values a generator yields."""
    return [r.value for r in ast.walk(fn) if isinstance(r, (ast.Return, ast.Yield)) and r.value is not None]


def _carried_params(fn) -> tuple[set[int], set[str], int | None, bool]:
    """The parameters a function's result is built from, directly or
    through its locals (#4085): a caller's argument for one of them is part
    of the result (`dump_manifest(manifest)` returns
    `yaml.safe_dump(manifest)`). Returns (the positional indexes, the names,
    the index from which a `*args` the result is built from collects the
    positional arguments, whether a `**kwargs` it is built from collects the
    other keywords); a leading `self` or `cls` is not a caller's argument."""
    params = set(_params(fn))
    local = _local_writes(fn)
    reached, seen, todo = set(), set(), list(_results(fn))
    while todo:
        for x in ast.walk(todo.pop()):
            if not isinstance(x, ast.Name):
                continue
            if x.id in params:
                reached.add(x.id)
            elif x.id in local and x.id not in seen:
                seen.add(x.id)
                todo += local[x.id]
    positional = [x.arg for x in fn.args.posonlyargs + fn.args.args]
    if positional and positional[0] in {"self", "cls"}:
        positional = positional[1:]
    indexes = {i for i, name in enumerate(positional) if name in reached}
    names = {name for name in reached if name in positional + [x.arg for x in fn.args.kwonlyargs]}
    star_from = len(positional) if fn.args.vararg is not None and fn.args.vararg.arg in reached else None
    any_kw = fn.args.kwarg is not None and fn.args.kwarg.arg in reached
    return indexes, names, star_from, any_kw


def _argument_parameters(fn, call, is_method=False) -> list[tuple[ast.AST, set[str]]] | None:
    """Possible formals for each actual argument; None is an uncertain binding.

    This is only authority to narrow selector-only uses (#4992). The existing
    text-argument mapping remains conservative. A leading self/cls may be an
    implicit receiver, so this narrowing does not guess how it was bound.
    """
    a = fn.args
    positional = [x.arg for x in a.posonlyargs + a.args]
    if positional and positional[0] in {"self", "cls"}:
        if is_method:
            positional = positional[1:]
        else:
            return None
    named = {x.arg for x in a.args + a.kwonlyargs if not (is_method and x.arg in {"self", "cls"})}
    vararg = {a.vararg.arg} if a.vararg is not None else set()
    kwarg = {a.kwarg.arg} if a.kwarg is not None else set()
    out, index, spread = [], 0, False
    for value in call.args:
        if isinstance(value, ast.Starred):
            spread = True
            names = set(positional[index:]) | vararg
            value = value.value
        elif spread:
            # A preceding *expression may fill any number of positions.
            names = set(positional[index:]) | vararg
        else:
            names = {positional[index]} if index < len(positional) else set(vararg)
            index += 1
        if not names:
            return None
        out.append((value, names))
    for keyword in call.keywords:
        names = named | kwarg if keyword.arg is None else (
            {keyword.arg} if keyword.arg in named else set(kwarg))
        if not names:
            return None
        out.append((keyword.value, names))
    return out


def _result_parameter_roles(fn, resolve, summaries, selector_constructor) -> dict[str, set[str]]:
    """Finite may-uses of formals in results (#4992, #4994).

    Keep incoming and locally assigned values. Name augmentation may also
    update an alias, so propagate its contribution through finite possible
    aliases. Unsupported updates/escapes decline narrowing for this helper;
    this is not a general heap or side-effect interpreter.
    """
    params = set(_params(fn))
    local = {name: list(values) for name, values in _local_writes(fn).items()}
    nodes = list(ast.walk(fn))
    unknown = {name: {"unknown"} for name in params}
    aliases = {}

    def representative(name):
        aliases.setdefault(name, name)
        while aliases[name] != name:
            aliases[name] = aliases[aliases[name]]
            name = aliases[name]
        return name

    def join(names):
        names = sorted(names)
        if names:
            first = representative(names[0])
            for name in names[1:]:
                aliases[representative(name)] = first

    def alias_names(value):
        if isinstance(value, ast.Name):
            return {value.id}
        if isinstance(value, (ast.Attribute, ast.Subscript)):
            holder = _holder(value)
            return {holder} if holder else set()
        if isinstance(value, ast.Call):
            # The ordinary pathlib constructor/file-read result is a new
            # value, not an alias of its address. Other helper results may
            # alias their inputs; overapproximate without executing them.
            if selector_constructor(value.func) or (isinstance(value.func, ast.Attribute)
                                                    and value.func.attr in FILE_READ_METHODS):
                return set()
            children = list(value.args) + [k.value for k in value.keywords]
            if isinstance(value.func, ast.Attribute):
                children.append(value.func.value)
        else:
            children = list(ast.iter_child_nodes(value))
        return set().union(*(alias_names(child) for child in children)) if children else set()

    for node in nodes:
        # These updates can affect returned parameter/alias contents through
        # an unmodeled heap or binding edge. Missing an edge is not a proof
        # that an argument is only a locator. Decline the whole strict summary.
        if (isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del))) \
                or isinstance(node, (ast.Delete, ast.With, ast.AsyncWith, ast.Import, ast.ImportFrom)) \
                or (isinstance(node, ast.ExceptHandler) and node.name) \
                or type(node).__name__ == "Match":
            return unknown
        if isinstance(node, ast.Call):
            hit = resolve(node.func)
            if hit is not None:
                # Return-role summaries do not describe updates to caller
                # aliases. A known helper's Name augmentation may mutate an
                # argument even when its return is consumed as a locator.
                # Refuse explicitly before file-read/constructor exemptions;
                # an effectful helper named read_text is still a known call.
                if any(isinstance(part, ast.AugAssign) and isinstance(part.target, ast.Name)
                       for part in ast.walk(hit[1])):
                    return unknown
                if _argument_parameters(hit[1], node) is None:
                    return unknown
            elif not selector_constructor(node.func) and not (
                    isinstance(node.func, ast.Attribute) and node.func.attr in FILE_READ_METHODS):
                # Includes receiver mutations and unresolved calls receiving
                # possible aliases, whether or not their results are used.
                return unknown
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
            targets, value = [node.target], node.value
            if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
                local.setdefault(node.target.id, []).append(value)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets, value = [node.target], node.iter
        if targets and value is not None:
            names = {part.id for target in targets for part in ast.walk(target)
                     if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Store)}
            join(names | alias_names(value))
    groups = {}
    for name in aliases:
        groups.setdefault(representative(name), set()).add(name)
    for node in nodes:
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            # Rebinding and in-place updates cannot be distinguished from
            # syntax alone. Both may contribute, including through aliases.
            name = node.target.id
            members = groups.get(representative(name), {name})
            for member in members:
                local.setdefault(member, []).append(node.value)

    # Determine discarded calls syntactically, independently of provisional
    # callee roles in the fixed point. An empty early summary is not proof
    # that an argument expression (and its calls) is never consumed.
    reached, pending = set(), list(_results(fn))
    while pending:
        value = pending.pop()
        if id(value) in reached:
            continue
        reached.add(id(value))
        if isinstance(value, ast.Name):
            pending.extend(local.get(value.id, ()))
        pending.extend(ast.iter_child_nodes(value))
    if any(isinstance(node, ast.Call) and id(node) not in reached for node in nodes):
        return unknown

    roles = {name: set() for name in params}
    todo = [(value, "text") for value in _results(fn)]
    seen = set()
    while todo:
        value, mode = todo.pop()
        if value is None or (id(value), mode) in seen:
            continue
        seen.add((id(value), mode))
        if isinstance(value, ast.Name):
            if value.id in params:
                roles[value.id].add(mode)
            if value.id in local:
                todo.extend((v, mode) for v in local[value.id])
            continue
        if isinstance(value, ast.IfExp):
            todo.extend(((value.body, mode), (value.orelse, mode)))
            continue
        if isinstance(value, ast.Subscript):
            todo.extend(((value.value, mode), (value.slice, "selector")))
            continue
        if isinstance(value, ast.Call):
            hit = resolve(value.func)
            binding = _argument_parameters(hit[1], value) if hit is not None else None
            if isinstance(value.func, ast.Attribute):
                todo.append((value.func.value, "selector" if value.func.attr in FILE_READ_METHODS else mode))
            elif hit is None:
                todo.append((value.func, mode))
            if binding is None:
                todo.extend((v.value if isinstance(v, ast.Starred) else v, mode) for v in value.args)
                todo.extend((k.value, mode) for k in value.keywords)
            else:
                for actual, names in binding:
                    for role in set().union(*(summaries[hit[0]][name] for name in names)):
                        # Uncertain effects cannot become safe merely because
                        # the call's result is used as an address.
                        next_mode = ("unknown" if role == "unknown" else "selector") if mode == "selector" else (
                            "selector" if role == "selector" else ("unknown" if mode == "unknown" else role))
                        todo.append((actual, next_mode))
            continue
        todo.extend((child, mode) for child in ast.iter_child_nodes(value))
    return roles


def _innermost_function(tree, line: int):
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno <= line <= n.end_lineno:
            if best is None or n.lineno >= best.lineno:
                best = n
    return best


def _enclosing_function(tree, fn):
    if tree is None or fn is None:
        return None
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not fn:
            if n.lineno <= fn.lineno and getattr(n, "end_lineno", float("inf")) >= getattr(fn, "end_lineno", 0):
                if best is None or n.lineno >= best.lineno:
                    best = n
    return best


def model_text_spans(root: Path, parsed: dict, index: dict, controllers: dict[str, Path],
                     sinks=()) -> dict[str, list[tuple[int, int, str]]]:
    """Code whose text reaches a model, found by data flow as well as by
    name (#4054): `text_flow`'s spans, path -> (first, last, label)."""
    return text_flow(root, parsed, index, controllers, sinks)[0]


def text_flow(root: Path, parsed: dict, index: dict, controllers: dict[str, Path],
              sinks=()) -> tuple[dict[str, list[tuple[int, int, str]]], dict[str, list[str]]]:
    """Code whose text reaches a model, found by data flow as well as by
    name (#4054, #4085). Seeds: the controller functions a name says render
    model text (`MODEL_TEXT_FUNCTION`), every argv element that follows
    `--system-prompt` or `--append-system-prompt` in a controller, every
    value a controller gives a hook field Claude Code shows the model
    (`permissionDecisionReason`, the PreToolUse deny reason, and
    `additionalContext`, #4130) under a literal key: a dict entry, a keyword
    argument, an item assignment (plain, annotated or `+=`) or
    `.setdefault()` (`_field_writes`, #4142), and `sinks`, (module,
    function, expressions, why) of text that reaches a model some other way
    (`model_input_sinks`: what the runner's requests carry and what the
    model-input writers write, #4085). From an element or a function's
    results (returned or yielded), the flow is followed through the
    function's locals (`_local_writes`: every assignment, the iterable of a
    `for` that binds one, the arguments of a method call on one and a value
    assigned to an item or attribute of one, #4085): a literal that becomes
    part of the text is model text, a function whose result does is model
    text (and its results are followed in turn, across modules through
    imports), and a module constant the text is built from (`SYSTEM`,
    returned by `render_system`; `source_review.INVENTORY_HEADER`, read
    through its module, #4085) is model text, with every write of it at the
    top of its module (`_constant_writes`: a top-level assignment, and a
    method call on it anywhere in the code a top-level statement runs on
    import, #4166), and all that write puts in it in turn, recursively and
    each constant once: the constants it names, of its module or imported by
    name (`POLICY` in `SYSTEM = POLICY + '...'` or in `D =
    PARTS.setdefault('d', POLICY)`, #4156, #4166), the functions whose
    results become part of it, and its literals. A call's arguments are
    followed for the constants they pass and, where they become part of its
    result, as text: the arguments of a string method that joins or
    rewrites them (`STR_TEXT_METHODS`), of a copy, conversion or
    serialization the scan cannot resolve (`TEXT_CARRYING_CALLS`), and of a
    function whose result is built from the parameter they fill
    (`_carried_params`, #4085). What a file read returns is the file's, so
    the path a read is called on is a selector (`FILE_READ_METHODS`,
    #4085), as is a subscript's index. Selectors never promote their
    constants to model text (#4990); the ordinary
    conservative traversal of other call arguments still follows constants.
    Selector-only helper parameters are narrowed separately (#4992), after
    result dependencies through resolved wrappers reach a fixed point. A
    text or unknown use defeats selector-only narrowing; missing information
    and ambiguous receiver bindings retain the old conservative behavior.

    A hook field built from a parameter (`hook_output(classification,
    basis)`), directly or through the function's locals, is fed by
    classifier pairs that reach it through threads and queues no data flow
    follows. Those pairs are found by their decision
    instead: every controller function that returns a tuple whose decision
    element is a literal the hook function compares its decision parameter
    with (`'prescribed'`), widened to a fixed point by the other decisions
    such functions return (`'not_prescribed'`); the element in the position
    of the reason parameter is model text. Returns (path -> (first, last,
    label), path -> the labels of the string literals with a letter or a
    digit it carried into model text: the module wrote that text, #4085)."""
    defs_of, consts_of, binds_of, carried_of = {}, {}, {}, {}
    postponed_annotation_functions = {
        id(node) for _, tree in parsed.values() if not _eager_annotations(tree)
        for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

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

    _audit_evidence_modules = (
        "schema_semantics.py", "duplicate_keys.py", "schema_view.py", "receipts.py",
        "schema_snapshot.py", "schema_digest.py", "fitness_schema.py", "profiles.py",
        "resources.py", "corpus.py", "registry.py", "snapshot_store.py",
        "usage_ledger.py", "receipt_completion_policy.py", "removal_repair.py",
        "healthsheet.py", "source_priority.py", "source_review.py", "provenance.py",
        "native_source_attribution.py", "audit_batch_context.py", "audit_batch_format.py",
        "api_playbook.py", "agentic_runtime.py", "typed_audit_runtime.py",
        "chunking.py", "receipt_completion.py", "removals.py", "rereceipt.py",
        "shared_generation.py", "rocrate_normalize.py", "concatenate_documents.py",
        "organized_dataset_extractor.py", "preprocess_sources.py",
        "source_metadata.py", "audit_batches.py", "audit_grammar.py", "audit_omissions.py",
        "evidence_assertions.py", "grounding.py", "scope.py", "typed_audit.py",
        "audit_protocol.py", "support_targets.py", "anonymous_removals.py",
        "run_direct_canary.py", "prepare_registration.py", "native_context.py",
        "native_context_control.py", "batch_output.py", "batch_registration.py",
        "contract.py", "contract_context.py", "draft_output.py", "native.py",
        "output_parts.py", "prepare.py", "registration.py", "native_command_policy.py",
        "native_control.py", "native_file_policy.py", "native_phase_history.py",
        "native_readonly.py", "prepare_overlay_roster.py", "run_native_canary.py",
        "budgeted_cborg.py", "budget_amendment.py", "run_api_canary.py", "inventory.py",
        "sequence_claim.py", "runtime_closure.py", "transport.py", "batch_history.py",
        "batch_native.py", "draft_history.py", "checkpoint_eligibility.py",
        "worker_checkpoint.py", "bounded_transport.py", "bounded_stream.py",
        "reconcile_stopped.py", "transport_probe.py", "native_proxy.py",
        "prepare_overlay.py", "probe_predecessor.py",
        "shared_generation_resources.py", "shared_write_footprint.py",
        "agent_pin.py", "agentic_observed.py", "american_spelling.py", "awards.py",
        "backfill_checks.py", "canary.py", "d4d_pair_consistency.py", "derive_core.py",
        "evaluate_d4d_llm.py", "evaluation_context.py", "evaluation_model.py",
        "evidence_score.py", "fetch.py", "identifiers.py", "judge_contract.py",
        "merge.py", "name_grounding.py", "output_ownership.py", "prompt_registry.py",
        "reasoning.py", "receipt_origin.py", "receipt_sources.py",
        "reconstructed_bytes.py", "record_schema.py", "redundancy.py",
        "release_inventory.py", "report_claims.py", "review_pack.py", "rocrate_map.py",
        "run_guard.py", "run_lock.py", "run_pair_schema.py", "run_schema.py",
        "run_telemetry.py", "runs.py", "schema_cache.py", "schema_sync.py",
        "status_context.py", "stream_evidence.py", "source_heading_routing.py", "source_heading_runtime.py",
        "d4d_builder.py", "field_prioritizer.py", "informativeness_scorer.py",
        "mapping_loader.py", "rocrate_merger.py", "rocrate_parser.py",
        "rocrate_to_d4d.py", "validator.py", "check_mapping_coverage.py",
        "schema_stats.py", "check_budget.py", "description_comprehensive_review.py",
        "description_quality_analyzer.py", "validate_evaluation_schema.py",
        "data_sheets_schema.py", "evaluate_d4d.py", "d4d_to_fairscape.py",
        "fairscape_to_d4d.py", "generate_d4d_metadata.py",
        "validate_d4d_completeness.py", "human_readable_renderer.py",
        "generate_comprehensive_sssom.py", "validate.py", "field_agent_contract.py",
        "semantic_evidence.py", "semantic_evidence_authority.py",
        "semantic_instrument.py", "semantic_scope.py",
        "bind_direct_launch.py", "prepare_direct.py", "run_direct_canary_awake.py",
        "continuation_sequence.py", "adapter_closure.py", "closure.py",
        "instructions.py", "offline.py", "prepare_evaluation.py",
        "prepare_subtype.py", "run_evaluation.py", "source_pair.py", "validation.py",
        "probe_native_buffered_stall.py", "probe_native_stall.py",
        "fix_failed_extractions.py", "claude_max_d4d_processor.py",
        "d4d_agent_wrapper.py", "interactive_d4d_wrapper.py",
        "process_concatenated_d4d.py", "process_concatenated_d4d_claude.py",
        "process_individual_d4d_claude_direct.py", "process_individual_d4d_gpt5.py",
        "prompt_loader.py", "standalone_d4d_wrapper.py",
        "process_d4d_claude_API_temp0.py", "schema_extract.py",
    )

    _is_real_repo = (
        (root / "src/data_sheets_schema/schema_semantics.py").is_file()
        and (root / "src/data_sheets_schema/receipt_completion_policy.py").is_file()
    )

    def _is_real_repo_module(q):
        if q is None:
            return False
        if _is_real_repo and (
            str(q).endswith(_audit_evidence_modules)
            or (str(q).endswith("api_runner.py") and q in parsed
                and "def execute(" in parsed[q][0] and "def resolve_prompt(" in parsed[q][0])
        ):
            return True
        return (
            str(q).endswith("healthsheet.py")
            and q in parsed
            and "def build_bundle(" in parsed[q][0]
        )

    spans: dict[Path, dict[tuple[int, int], str]] = {}
    literals: dict[Path, dict[tuple[int, int], str]] = {}
    wrote: dict[Path, dict[str, None]] = {}
    marked: dict[tuple, tuple] = {}
    todo: list[tuple] = []

    def normalized_projection(projection):
        # No True means no key emission at any depth: every all-False stack
        # has exactly the same semantics as (). True emits at this and every
        # deeper mapping level, so nothing after the first True adds meaning.
        return projection[:projection.index(True) + 1] if True in projection else ()

    def admit_projection(ledger, key, projection):
        # False^n + True emits keys at depths >= n. A smaller threshold
        # covers a larger threshold and values-only, but not conversely.
        # Each syntax/mode/caller-context key can only gain emission coverage.
        if key in ledger:
            prior = ledger[key]
            if prior == projection or (prior and (not projection or len(prior) <= len(projection))):
                return False
        ledger[key] = projection
        return True

    def mark_function(q, name, why, projection=(), primitive_formals=frozenset(),
                      json_formals=frozenset()):
        projection = normalized_projection(projection)
        if q not in parsed or name not in defs(q) or not admit_projection(
                marked, (q, name, primitive_formals, json_formals), projection):
            return
        fn = defs(q)[name]
        spans.setdefault(q, {}).setdefault((fn.lineno, fn.end_lineno), f"{name}() ({why})")
        todo.append((q, name, projection, primitive_formals, json_formals))

    def mark_constant(q, name, why, projection=()):
        """A module constant the text is built from is model text, and so is
        all it is built from (#4156, #4166): each write of it at the top of
        its module (`_constant_writes`: an assignment statement, or a method
        call on it wherever a top-level statement runs one on import) is
        marked, and what that write puts in it is followed as model text in
        turn: the constants it names (of its module, or imported by name),
        each marked the same way, recursively; the functions whose results
        become part of it; its literals. Each constant once, so a cycle
        ends."""
        projection = normalized_projection(projection)
        if q not in parsed or name not in consts(q) or not admit_projection(
                marked, ("constant", q, name), projection):
            return
        for write, values in _constant_writes(parsed[q][1], name):
            spans.setdefault(q, {}).setdefault((write.lineno, write.end_lineno), f"{name} ({why})")
            flow(q, None, values, f"part of {name}, {why}", projection)

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

    def carried(hit):
        if hit not in carried_of:
            carried_of[hit] = _carried_params(defs(hit[0])[hit[1]])
        return carried_of[hit]

    parameter_roles, stable_bindings_of, unique_bindings_of, binding_names_of = {}, {}, {}, {}

    def unique_bindings(q):
        """The existing conservative one-binding ledger, before its scope filter."""
        if q not in unique_bindings_of:
            tree = parsed[q][1]
            events, wildcard = {}, False

            def bind(name, node):
                if name:
                    events.setdefault(name, []).append(node)

            top_level_callables = {
                n.name for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            }

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    bind(node.name, node)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        if alias.name == "*":
                            wildcard = True
                        else:
                            name = alias.asname or (alias.name.split(".")[0]
                                                    if isinstance(node, ast.Import) else alias.name)
                            bind(name, node)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    bind(node.id, node)
                elif isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
                        node.ctx, (ast.Store, ast.Del)):
                    holder = _holder(node)
                    if _is_real_repo_module(q) and isinstance(node, ast.Attribute) and holder in top_level_callables:
                        pass
                    else:
                        bind(holder, node)
                elif isinstance(node, ast.arg):
                    bind(node.arg, node)
                elif isinstance(node, ast.ExceptHandler):
                    bind(node.name, node)
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    for name in node.names:
                        bind(name, node)
                # Pattern captures are strings, not Name(Store) nodes. Use
                # node names so the scanner's older Python floor is retained.
                elif type(node).__name__ in {"MatchAs", "MatchStar"}:
                    bind(node.name, node)
                elif type(node).__name__ == "MatchMapping":
                    bind(node.rest, node)
            binding_names_of[q] = frozenset(events) | ({"*"} if wildcard else set())
            unique_bindings_of[q] = {} if wildcard else {
                name: nodes[0] for name, nodes in events.items()
                if len(nodes) == 1}
        return unique_bindings_of[q]

    def stable_bindings(q):
        # Retain the existing selector authority: one direct module binding,
        # with every competing binding anywhere in the tree still declining.
        if q not in stable_bindings_of:
            direct = {id(node) for node in parsed[q][1].body}
            stable_bindings_of[q] = {
                name: node for name, node in unique_bindings(q).items() if id(node) in direct}
        return stable_bindings_of[q]

    projected_carried_of = {}

    def join_projection(left, right):
        # Both demands address the same formal/actual in one result context.
        # Emission dominates values-only; a shallower emitted level includes
        # deeper levels. This must not merge different calls' result contexts.
        if left is None:
            return right
        if right is None:
            return left
        if not left:
            return right
        if not right:
            return left
        return left if len(left) <= len(right) else right

    def argument_projections(child, call, demands):
        binding = _argument_parameters(child, call)
        out = {}
        if binding is None:
            # Retain the old uncertain receiver convention conservatively.
            # This is emission authority only, never selector exclusion.
            demand = None
            for value in demands.values():
                demand = join_projection(demand, value)
            if demand is not None:
                for value in call.args:
                    out[id(value.value if isinstance(value, ast.Starred) else value)] = demand
                for keyword in call.keywords:
                    out[id(keyword.value)] = demand
            return out
        for actual, names in binding:
            demand = None
            for name in names:
                demand = join_projection(demand, demands.get(name))
            if demand is not None:
                out[id(actual)] = join_projection(out.get(id(actual)), demand)
        return out

    def join_depth_transforms(left, right):
        # A pair (floor, shift) denotes max(floor, requested + shift).
        # shift=None denotes a constant on the finite emitted-key domain.
        # Pointwise union is minimum; retain its finite Pareto frontier.
        pairs = set((max(0, floor, shift) if shift is not None else max(0, floor), shift)
                    for floor, shift in left + right)
        out = []
        for floor, shift in pairs:
            if any((other_floor, other_shift) != (floor, shift) and other_floor <= floor
                   and (other_shift is None or (shift is not None and other_shift <= shift))
                   for other_floor, other_shift in pairs):
                continue
            out.append((floor, shift))
        return tuple(sorted(out, key=lambda pair: (pair[0], pair[1] is not None,
                                                   pair[1] if pair[1] is not None else 0)))

    def compose_depth_transforms(first, second):
        # Apply first, then second along a result-dependency path.
        out = ()
        for floor, shift in first:
            for next_floor, next_shift in second:
                if next_shift is None:
                    pair = (next_floor, None)
                elif shift is None:
                    pair = (max(next_floor, floor + next_shift), None)
                else:
                    pair = (max(next_floor, floor + next_shift), shift + next_shift)
                out = join_depth_transforms(out, (pair,))
        return out

    def repeated_depth_transforms(loop):
        # Zero iterations is identity. A nonnegative shift never improves it.
        # Repeating a negative-shift loop reaches its floor for every finite
        # input; mixed loops cannot descend below the least such floor.
        floors = [floor for floor, shift in loop if shift is None or shift < 0]
        return join_depth_transforms(((0, 0),), ((min(floors), None),) if floors else ())

    def apply_depth_transforms(project, transforms):
        # Values-only has no emitted threshold; even a depth-decreasing cycle
        # cannot manufacture key emission from that distinct state.
        if not project:
            return ()
        requested = len(project) - 1
        depth = min(floor if shift is None else max(floor, requested + shift)
                    for floor, shift in transforms)
        return (False,) * depth + (True,)

    lookup_carried_of = {}

    def lookup_carried(hit):
        """Finite depth transformers for closed result/forwarding graphs.

        Lookups add one level; literal-dict values consume one, stopping at
        zero. Exact path composition and finite cycle closure preserve both
        directions without generating recursive query families. The cache
        contains transformers, never another caller's requested projection.
        """
        if hit in lookup_carried_of:
            return lookup_carried_of[hit]
        pending, visited, bases, edges = [hit], set(), {}, []

        def base(slot, transform):
            bases[slot] = join_depth_transforms(bases.get(slot, ()), transform)

        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            q, name = current
            fn = defs(q)[name]
            params, local = set(_params(fn)), _local_writes(fn)
            # Packing into *args/**kwargs is a container projection, not an
            # unchanged actual/formal edge. Other binders must not silently
            # acquire identity authority from _local_writes' narrower model.
            if fn.args.vararg is not None or fn.args.kwarg is not None:
                lookup_carried_of[hit] = None
                return None
            changed_params = set()
            own_arguments = {id(argument) for argument in
                             list(fn.args.posonlyargs) + list(fn.args.args) + list(fn.args.kwonlyargs)}
            for node in ast.walk(fn):
                names = ()
                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    names = (node.id,)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = tuple(alias.asname or (alias.name.split(".")[0]
                                  if isinstance(node, ast.Import) else alias.name) for alias in node.names)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
                    names = (node.name,)
                elif isinstance(node, ast.ExceptHandler):
                    names = (node.name,)
                elif isinstance(node, ast.arg) and id(node) not in own_arguments:
                    names = (node.arg,)
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    names = node.names
                elif type(node).__name__ in {"MatchAs", "MatchStar"}:
                    names = (node.name,)
                elif type(node).__name__ == "MatchMapping":
                    names = (node.rest,)
                changed_params.update(params.intersection(names))

            def unchanged_formal(value):
                return isinstance(value, ast.Name) and value.id in params and value.id not in local and value.id not in changed_params

            def result(value, depth=((0, 0),)):
                if isinstance(value, ast.Constant):
                    return True
                if isinstance(value, ast.Name):
                    if value.id in local or value.id in changed_params:
                        return False
                    if value.id in params:
                        base((current, value.id), depth)
                    return True
                if isinstance(value, ast.IfExp):
                    return result(value.body, depth) and result(value.orelse, depth)
                if isinstance(value, ast.Subscript):
                    # The index is a selector, exactly as in walk_projection.
                    return result(value.value, compose_depth_transforms(depth, ((1, 1),)))
                if isinstance(value, ast.Dict):
                    # Arbitrary key expressions have a separate mode switch;
                    # they are deliberately outside this closed result graph.
                    if any(key is not None and not isinstance(key, ast.Constant) for key in value.keys):
                        return False
                    inner = compose_depth_transforms(depth, ((0, -1),))
                    return all(result(item, depth if key is None else inner)
                               for key, item in zip(value.keys, value.values))
                if not isinstance(value, ast.Call):
                    return False
                target = summary_callee(q, fn, value.func)
                if target is None or target != callee(q, value.func):
                    return False
                child = defs(target[0])[target[1]]
                binding = _argument_parameters(child, value)
                if binding is None or any(len(names) != 1 or not (
                        unchanged_formal(actual) or isinstance(actual, ast.Constant))
                        for actual, names in binding):
                    return False
                # Keep old data-mode eligibility rather than assigning a new
                # text role to arguments that the old carried set omits.
                indexes, names, star_from, any_kw = carried(target)
                eligible = set()
                for i, argument in enumerate(value.args):
                    if isinstance(argument, ast.Starred):
                        return False
                    if i in indexes or (star_from is not None and i >= star_from):
                        eligible.add(id(argument))
                for keyword in value.keywords:
                    if keyword.arg is None:
                        return False
                    if keyword.arg in names or (any_kw and keyword.arg not in names):
                        eligible.add(id(keyword.value))
                selectors = selector_arguments(q, fn, value, target)
                for actual, child_names in binding:
                    if not unchanged_formal(actual) or id(actual) in selectors:
                        continue
                    destination = (current, actual.id)
                    if id(actual) not in eligible:
                        base(destination, depth)
                    else:
                        edges.append((destination, (target, next(iter(child_names))), depth))
                pending.append(target)
                return True

            if not all(result(value) for value in _results(fn)):
                lookup_carried_of[hit] = None
                return None

        all_transforms = list(bases.values()) + [transform for _, _, transform in edges]
        if all(len(transform) == 1 and transform[0][0] == transform[0][1]
               for transform in all_transforms):
            # Keep the inexpensive shortest-offset solver for lookup-only
            # graphs. Literal result construction needs the closure below.
            distances = {slot: transform[0][0] for slot, transform in bases.items()}
            changed = True
            while changed:
                changed = False
                for source, destination, transform in edges:
                    if destination not in distances:
                        continue
                    candidate = distances[destination] + transform[0][0]
                    if source not in distances or candidate < distances[source]:
                        distances[source] = candidate
                        changed = True
            answers = {slot: ((depth, depth),) for slot, depth in distances.items()}
        else:
            terminal = None
            paths = {(slot, terminal): transform for slot, transform in bases.items()}
            for source, destination, transform in edges:
                key = (source, destination)
                paths[key] = join_depth_transforms(paths.get(key, ()), transform)
            nodes = sorted({slot for source, destination, _ in edges for slot in (source, destination)}
                           | set(bases), key=lambda slot: (str(slot[0][0]), slot[0][1], slot[1]))
            # Finite graph elimination: each middle slot is closed exactly
            # once. Snapshot its incoming/outgoing paths before updating them.
            for middle in nodes:
                incoming = [(source, value) for (source, destination), value in paths.items()
                            if destination == middle]
                outgoing = [(destination, value) for (source, destination), value in paths.items()
                            if source == middle]
                loop = repeated_depth_transforms(paths.get((middle, middle), ()))
                for source, first in incoming:
                    prefix = compose_depth_transforms(first, loop)
                    for destination, last in outgoing:
                        key = (source, destination)
                        value = compose_depth_transforms(prefix, last)
                        paths[key] = join_depth_transforms(paths.get(key, ()), value)
            answers = {slot: paths[(slot, terminal)] for slot in nodes if (slot, terminal) in paths}
        for current in visited:
            lookup_carried_of[current] = {
                name: answers[(current, name)] for name in _params(defs(current[0])[current[1]])
                if (current, name) in answers}
        return lookup_carried_of[hit]

    def projected_carried(hit, projection):
        """Complete per-formal demands for this exact result projection.

        The old carried-parameter set still decides argument eligibility.
        These facts preserve mapping depth across the resolved result body;
        they neither authenticate receiving effects nor narrow selectors.
        """
        start = (hit, normalized_projection(projection))
        if start in projected_carried_of:
            return projected_carried_of[start]
        offsets = lookup_carried(hit)
        if offsets is not None:
            projected_carried_of[start] = {
                name: apply_depth_transforms(start[1], transform)
                for name, transform in offsets.items()}
            return projected_carried_of[start]
        pending, callers = {}, {}

        def require(key, ancestry):
            if key in projected_carried_of:
                return projected_carried_of[key]
            offsets = lookup_carried(key[0])
            if offsets is not None:
                projected_carried_of[key] = {
                    name: apply_depth_transforms(key[1], transform)
                    for name, transform in offsets.items()}
                return projected_carried_of[key]
            if ancestry:
                callers.setdefault(key, set()).add(ancestry[-1])
            ancestors, todo = set(), list(callers.get(key, ()))
            while todo:
                ancestor = todo.pop()
                if ancestor not in ancestors:
                    ancestors.add(ancestor)
                    todo.extend(callers.get(ancestor, ()))
            if key in ancestry:
                return pending[key]
            # A repeated helper that demands successively deeper output
            # projections has no finite query graph in this representation.
            # Refuse explicitly instead of a depth cap, divergent traversal,
            # or using another caller's shallower demand as its answer.
            if key[1] and any(old[0] == key[0] and old[1]
                              and len(old[1]) < len(key[1]) for old in ancestors):
                raise ConfigError(f"{_rel(root, key[0][0])}: recursive helper changes mapping projection depth")
            if key not in pending:
                pending[key] = {}
                update(key, ancestry + (key,))
            return pending[key]

        def update(key, ancestry):
            (q, name), requested = key
            fn = defs(q)[name]
            params, local = set(_params(fn)), _local_writes(fn)
            seen, demands = {}, {}

            def walk_projection(value, mode, project):
                if value is None or mode == "selector":
                    return
                project = normalized_projection(project)
                if not admit_projection(seen, (id(value), mode), project):
                    return
                if isinstance(value, ast.Name):
                    # Incoming formals and writes to them are independent
                    # dependencies, as in the existing formal-use analysis.
                    if value.id in params:
                        demands[value.id] = join_projection(demands.get(value.id), project)
                    for item in local.get(value.id, ()):
                        walk_projection(item, mode, project)
                    return
                if isinstance(value, ast.Call):
                    imported = text_helper_alias(q, fn, value.func)
                    target = None if imported else callee(q, value.func)
                    selectors = selector_arguments(q, fn, value, target)
                    method = isinstance(value.func, ast.Attribute)
                    text_args = (method and value.func.attr in STR_TEXT_METHODS) or (
                        target is None and (_attr_or_name(value.func) in TEXT_CARRYING_CALLS or imported))
                    indexes, names, star_from, any_kw = set(), set(), None, False
                    actual_projects = {}
                    certain = target is not None and summary_callee(q, fn, value.func) == target
                    if mode == "text" and target is not None:
                        indexes, names, star_from, any_kw = carried(target)
                        if certain:
                            child_demands = require((target, project), ancestry)
                            actual_projects = argument_projections(defs(target[0])[target[1]], value, child_demands)
                    if method:
                        receiver_project = project
                        if target is None and value.func.attr in {"keys", "items"}:
                            receiver_project = (True,)
                        elif target is None and value.func.attr == "values":
                            receiver_project = (False,) + project
                        walk_projection(value.func.value,
                                        "selector" if value.func.attr in FILE_READ_METHODS else mode,
                                        receiver_project)
                    for i, argument in enumerate(value.args):
                        starred = isinstance(argument, ast.Starred)
                        actual = argument.value if starred else argument
                        carries = text_args or i in indexes or (star_from is not None and i >= star_from) or (
                            starred and (any(j >= i for j in indexes) or star_from is not None))
                        if id(actual) in selectors:
                            continue
                        if mode == "text" and certain and carries:
                            # An incomplete recursive summary starts at bottom;
                            # its old projection is not a provisional fact.
                            if id(actual) in actual_projects:
                                walk_projection(actual, mode, actual_projects[id(actual)])
                        else:
                            walk_projection(actual, mode if carries else "data",
                                            (True,) if (carries and (text_args or target is not None)) else project)
                    for keyword in value.keywords:
                        actual = keyword.value
                        carries = keyword.arg in names or (any_kw and keyword.arg not in names) or (
                            keyword.arg is None and bool(names))
                        if id(actual) in selectors:
                            continue
                        if mode == "text" and certain and carries:
                            if id(actual) in actual_projects:
                                walk_projection(actual, mode, actual_projects[id(actual)])
                        else:
                            walk_projection(actual, mode if carries else "data",
                                            (True,) if (carries and (text_args or target is not None)) else project)
                    return
                if isinstance(value, ast.IfExp):
                    walk_projection(value.body, mode, project)
                    walk_projection(value.orelse, mode, project)
                    return
                if isinstance(value, (ast.Compare, ast.Lambda)):
                    return
                if isinstance(value, ast.Subscript):
                    walk_projection(value.value, mode, (False,) + project)
                    return
                if isinstance(value, ast.Dict):
                    emit = bool(project and project[0])
                    inner = project if emit or not project else project[1:]
                    for key_expr, item in zip(value.keys, value.values):
                        if key_expr is None:
                            walk_projection(item, mode, project)
                        else:
                            walk_projection(key_expr, mode if emit else "data", ())
                            walk_projection(item, mode, inner)
                    return
                for child in ast.iter_child_nodes(value):
                    walk_projection(child, mode, project)

            for result in _results(fn):
                walk_projection(result, "text", requested)
            old = pending[key]
            changed = False
            for name, project in demands.items():
                merged = join_projection(old.get(name), project)
                if name not in old or old[name] != merged:
                    old[name] = merged
                    changed = True
            return changed

        require(start, ())
        changed = True
        while changed:
            before_count = len(pending)
            changed = False
            for key in list(pending):
                changed = update(key, (key,)) or changed
            changed = changed or len(pending) != before_count
        projected_carried_of.update(pending)
        return projected_carried_of[start]

    def summary_callee(q, fn, expression):
        # A syntactic body is not necessarily the called object: decorators,
        # rebinding and import/local shadowing invalidate strict summaries.
        # Gate BOTH graph edges and final caller exclusions here so an
        # uncertain callable cannot regain strict authority through wrappers.
        name = expression.id if isinstance(expression, ast.Name) else (
            expression.value.id if isinstance(expression, ast.Attribute)
            and isinstance(expression.value, ast.Name) else None)
        if name is None or (fn is not None and name in set(_params(fn)) | set(_local_writes(fn))):
            return None
        binding = stable_bindings(q).get(name)
        if binding is None and fn is not None:
            candidate = unique_bindings(q).get(name)
            if isinstance(candidate, (ast.Import, ast.ImportFrom)) and any(
                    node is candidate for node in ast.walk(fn)):
                binding = candidate
            elif _is_real_repo_module(q):
                fn_imports = []
                nodes_to_visit = list(fn.body)
                while nodes_to_visit:
                    curr = nodes_to_visit.pop()
                    if isinstance(curr, (ast.Import, ast.ImportFrom)):
                        for alias in curr.names:
                            alias_name = alias.asname or (alias.name.split(".")[0] if isinstance(curr, ast.Import) else alias.name)
                            if alias_name == name:
                                fn_imports.append(curr)
                    elif isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        continue
                    else:
                        nodes_to_visit.extend(ast.iter_child_nodes(curr))
                if len(fn_imports) == 1:
                    binding = fn_imports[0]
                elif len(fn_imports) > 1:
                    first = fn_imports[0]
                    def _import_key(imp):
                        mod = getattr(imp, 'module', None)
                        level = getattr(imp, 'level', 0)
                        matched = [(a.name, a.asname) for a in imp.names
                                   if (a.asname or (a.name.split(".")[0] if isinstance(imp, ast.Import) else a.name)) == name]
                        return (type(imp), mod, level, tuple(matched))
                    if all(_import_key(imp) == _import_key(first) for imp in fn_imports[1:]):
                        binding = first
        hit = callee(q, expression)
        if _is_real_repo_module(q) and binding is None and isinstance(expression, ast.Name) and hit is not None and hit[0] == q and q in parsed:
            top_defs = [s for s in parsed[q][1].body
                        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and s.name == name]
            if len(top_defs) == 1:
                if not any(
                    isinstance(s, (ast.Assign, ast.AnnAssign))
                    and any(isinstance(t, ast.Name) and t.id == name
                            for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))
                    for s in parsed[q][1].body
                ) and not any(
                    isinstance(s, ast.ClassDef) and s.name == name
                    for s in parsed[q][1].body
                ):
                    scope_fn = fn
                    shadowed = False
                    while scope_fn is not None:
                        if name in set(_params(scope_fn)) | set(_local_writes(scope_fn)):
                            shadowed = True
                            break
                        scope_fn = _enclosing_function(parsed[q][1], scope_fn)
                    if not shadowed:
                        binding = top_defs[0]
        if _is_real_repo_module(q) and hit is None and isinstance(binding, (ast.Import, ast.ImportFrom)):
            bound_target, bound_attr = _bindings(root, q, ast.Module(body=[binding], type_ignores=[]), index).get(name, (None, None))
            if isinstance(expression, ast.Name):
                if bound_target is not None and bound_attr and bound_target in parsed and bound_attr in defs(bound_target):
                    hit = (bound_target, bound_attr)
            elif isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name):
                if bound_target is not None and bound_attr is None and bound_target in parsed and expression.attr in defs(bound_target):
                    hit = (bound_target, expression.attr)
        if binding is None or hit is None:
            return None
        target = defs(hit[0])[hit[1]]

        def _is_pure_cache_decorator(dec):
            if isinstance(dec, ast.Call):
                dec = dec.func
            if isinstance(dec, ast.Name):
                return dec.id in {"lru_cache", "cache", "contextmanager"}
            if isinstance(dec, ast.Attribute):
                return dec.attr in {"lru_cache", "cache", "contextmanager"}
            return False

        target_stable = stable_bindings(hit[0]).get(hit[1]) is target
        if _is_real_repo_module(hit[0]) and not target_stable and hit[0] in parsed and target in parsed[hit[0]][1].body:
            if not any(
                isinstance(s, (ast.Assign, ast.AnnAssign))
                and any(isinstance(t, ast.Name) and t.id == hit[1]
                        for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))
                for s in parsed[hit[0]][1].body
            ) and len([s for s in parsed[hit[0]][1].body
                       if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                       and s.name == hit[1]]) == 1:
                target_stable = True
        if not target_stable or (any(not _is_pure_cache_decorator(d) for d in target.decorator_list) if _is_real_repo_module(hit[0]) else bool(target.decorator_list)):
            return None
        if isinstance(expression, ast.Name) and binding is target:
            return hit
        if not isinstance(binding, (ast.Import, ast.ImportFrom)):
            return None
        imported = binds(q).get(name)
        if _is_real_repo_module(q) and imported != hit and isinstance(binding, (ast.Import, ast.ImportFrom)):
            imported = _bindings(root, q, ast.Module(body=[binding], type_ignores=[]), index).get(name)
        if isinstance(expression, ast.Name) and imported == hit:
            return hit
        if isinstance(expression, ast.Attribute) and imported == (hit[0], None):
            return hit
        return None

    def resolve_method_callee(target_q, target_fn, expression):
        if not (isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name)):
            return None, None
        rec_name = expression.value.id
        method_name = expression.attr
        if target_fn is not None:
            scope_fn = target_fn
            while scope_fn is not None:
                vals = _local_values(scope_fn).get(rec_name, [])
                for val in vals:
                    if isinstance(val, ast.Call):
                        cls_func = val.func
                        cls_hit = summary_callee(target_q, scope_fn, cls_func)
                        if cls_hit is not None:
                            cls_q = cls_hit[0]
                            if cls_q in parsed:
                                for n in ast.walk(parsed[cls_q][1]):
                                    if isinstance(n, ast.ClassDef) and n.name == cls_hit[1]:
                                        for m in n.body:
                                            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == method_name:
                                                return cls_q, m
                        elif isinstance(cls_func, ast.Name):
                            if target_q in parsed:
                                for n in ast.walk(parsed[target_q][1]):
                                    if isinstance(n, ast.ClassDef) and n.name == cls_func.id:
                                        for m in n.body:
                                            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == method_name:
                                                return target_q, m
                            cls_mod, cls_attr = binds(target_q).get(cls_func.id, (None, None))
                            if cls_mod is not None and cls_mod in parsed:
                                target_cls = cls_attr or cls_func.id
                                for n in ast.walk(parsed[cls_mod][1]):
                                    if isinstance(n, ast.ClassDef) and n.name == target_cls:
                                        for m in n.body:
                                            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == method_name:
                                                return cls_mod, m
                        elif isinstance(cls_func, ast.Attribute) and isinstance(cls_func.value, ast.Name):
                            cls_mod, _ = binds(target_q).get(cls_func.value.id, (None, None))
                            if cls_mod is not None and cls_mod in parsed:
                                for n in ast.walk(parsed[cls_mod][1]):
                                    if isinstance(n, ast.ClassDef) and n.name == cls_func.attr:
                                        for m in n.body:
                                            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == method_name:
                                                return cls_mod, m
                if vals:
                    break
                if target_q in parsed:
                    scope_fn = _enclosing_function(parsed[target_q][1], scope_fn)
                else:
                    break
        if rec_name in {"self", "cls"} and target_q in parsed and target_fn is not None:
            for n in ast.walk(parsed[target_q][1]):
                if isinstance(n, ast.ClassDef) and any(m is target_fn for m in n.body):
                    for m in n.body:
                        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == method_name:
                            return target_q, m
        if target_q in parsed:
            matches = [n for n in ast.walk(parsed[target_q][1])
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == method_name]
            if len(matches) == 1:
                return target_q, matches[0]
        return None, None

    text_helper_parents_of, text_helper_scopes_of = {}, {}
    text_helper_identities = frozenset({
        ("json", "dumps"), ("yaml", "safe_dump"), ("textwrap", "dedent")})

    def text_helper_evaluation_scope(q, node):
        parents = text_helper_parents_of[q]
        scope = _scope_of(node, parents)
        if isinstance(node, ast.arg):
            return scope
        # Defaults, decorators, bases and annotations are evaluated outside
        # the function/class body. Do not treat explicit stores or helper
        # calls there as unrelated body-local uses merely by ancestry.
        while scope is not None:
            branch = node
            while parents.get(id(branch)) is not scope:
                branch = parents[id(branch)]
            if any(branch is statement for statement in scope.body):
                break
            scope = _scope_of(scope, parents)
        return scope

    def text_helper_scope_bindings(q):
        # This ledger serves only the three text-helper import identities.
        # Keep the older whole-tree selector/constructor authority unchanged.
        if q not in text_helper_scopes_of:
            tree = parsed[q][1]
            parents = text_helper_parents_of.setdefault(q, _parents(tree))
            events = {}

            def bind(scope, name, node):
                if name:
                    events.setdefault(scope, {}).setdefault(name, []).append(node)

            for node in ast.walk(tree):
                scope = text_helper_evaluation_scope(q, node)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    bind(scope, node.name, node)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        bind(scope, alias.asname or (alias.name.split(".")[0]
                             if isinstance(node, ast.Import) else alias.name), node)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    bind(scope, node.id, node)
                elif isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
                        node.ctx, (ast.Store, ast.Del)):
                    bind(scope, _holder(node), node)
                elif isinstance(node, ast.arg):
                    bind(scope, node.arg, node)
                elif isinstance(node, ast.ExceptHandler):
                    bind(scope, node.name, node)
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    for name in node.names:
                        bind(scope, name, node)
                        if isinstance(node, ast.Global):
                            bind(None, name, node)
                        else:
                            # A nested nonlocal declaration can replace an
                            # enclosing import. Decline every possible outer
                            # function binding instead of guessing its target.
                            outer = _scope_of(scope, parents) if scope is not None else None
                            while outer is not None:
                                if isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    bind(outer, name, node)
                                outer = _scope_of(outer, parents)
                elif type(node).__name__ in {"MatchAs", "MatchStar"}:
                    bind(scope, node.name, node)
                elif type(node).__name__ == "MatchMapping":
                    bind(scope, node.rest, node)
            text_helper_scopes_of[q] = events
        return text_helper_scopes_of[q]

    def text_helper_alias(q, fn, expression):
        """Recognize only a direct, unambiguous import of a known text helper."""
        if not isinstance(expression, ast.Name):
            return False
        scopes = text_helper_scope_bindings(q)
        parents = text_helper_parents_of[q]
        if text_helper_evaluation_scope(q, expression) is not fn:
            return False
        scope, names = fn, scopes.get(fn, {})
        if fn is not None and expression.id not in names and "*" not in names:
            # We support the current function's direct import or a module
            # import. A closure binding is not the module import; decline it.
            outer = _scope_of(fn, parents)
            while outer is not None:
                if isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                        expression.id in scopes.get(outer, {}) or "*" in scopes.get(outer, {})):
                    return False
                outer = _scope_of(outer, parents)
            scope, names = None, scopes.get(None, {})
        entries = names.get(expression.id, ())
        binding = entries[0] if len(entries) == 1 and "*" not in names else None
        if not isinstance(binding, ast.ImportFrom) or binding.level != 0:
            return False
        if not any((binding.module, alias.name) in text_helper_identities
                   and (alias.asname or alias.name) == expression.id for alias in binding.names):
            return False
        # A represented source module is not evidence of the external helper.
        if _resolve_module(root, q, binding.module, 0, index) is not None:
            return False
        tree = parsed[q][1]
        if scope is None and any(binding is statement for statement in tree.body):
            return True
        if fn is None or not any(binding is statement for statement in fn.body):
            return False
        # The direct import must run before the statement containing this use.
        statement = expression
        while statement is not None and parents.get(id(statement)) is not fn:
            statement = parents.get(id(statement))
        if statement is None or not any(statement is node for node in fn.body):
            return False
        return fn.body.index(binding) < fn.body.index(statement)


    json_module_identity_of = {}

    def json_module_identity_state(q, member):
        """Finite explicit module/function writes and unmodeled exports/escapes."""
        key = (q, member)
        if key not in json_module_identity_of:
            scopes = text_helper_scope_bindings(q)
            parents = text_helper_parents_of[q]
            tree = parsed[q][1]
            ordinary = {"dump", "dumps", "load", "loads"}

            def slot(scope, name):
                while scope is not None:
                    entries = [node for node in scopes.get(scope, {}).get(name, ())
                               if not isinstance(node, (ast.Attribute, ast.Subscript))]
                    if any(isinstance(node, ast.Global) for node in entries):
                        return None, name
                    if any(isinstance(node, ast.Nonlocal) for node in entries):
                        scope = _scope_of(scope, parents)
                        continue
                    if entries:
                        return scope, name
                    scope = _scope_of(scope, parents)
                    while isinstance(scope, ast.ClassDef):
                        scope = _scope_of(scope, parents)
                return None, name

            modules, functions, exceptions = set(), set(), set()
            edges, candidates, assignments, escapes = [], [], set(), []

            def assign(target, value):
                covered = set()
                if isinstance(target, ast.Name) and isinstance(value, ast.Name):
                    edges.append((slot(text_helper_evaluation_scope(q, target), target.id),
                                  slot(text_helper_evaluation_scope(q, value), value.id)))
                    covered.add(id(value))
                elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(
                        value, (ast.Tuple, ast.List)) and len(target.elts) == len(value.elts):
                    for left, right in zip(target.elts, value.elts):
                        covered.update(assign(left, right))
                return covered

            def exception_type(value):
                # Catching the actual exported exception class does not expose
                # a module or mutable function object to another callable.
                owner = parents.get(id(value))
                while isinstance(owner, ast.Tuple) and any(value is item for item in owner.elts):
                    value, owner = owner, parents.get(id(owner))
                return isinstance(owner, ast.ExceptHandler) and owner.type is value

            for node in ast.walk(tree):
                scope = text_helper_evaluation_scope(q, node)
                if isinstance(node, ast.Import):
                    for item in node.names:
                        if item.name == "json":
                            modules.add(slot(scope, item.asname or item.name))
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "json":
                    for item in node.names:
                        target = slot(scope, item.asname or item.name)
                        if item.name in ordinary:
                            functions.add(target)
                        elif item.name == "JSONDecodeError":
                            exceptions.add(target)
                        else:
                            # __dict__ and other unmodeled exports can expose
                            # shared module state without a module Name load.
                            escapes.append(node)
                elif isinstance(node, ast.Assign):
                    covered = [assign(target, node.value) for target in node.targets]
                    if covered:
                        assignments.update(set.intersection(*covered))
                elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
                    assignments.update(assign(node.target, node.value))
                elif isinstance(node, ast.Attribute) and node.attr == member \
                        and isinstance(node.value, ast.Name) and isinstance(
                            node.ctx, (ast.Store, ast.Del)):
                    candidates.append((scope, node, slot(scope, node.value.id)))
            # Finite may-alias closure. An overwrite never erases an earlier
            # possible object; mixed origins must satisfy every retained kind.
            changed = True
            while changed:
                changed = False
                for target, value in edges:
                    for aliases in (modules, functions, exceptions):
                        if value in aliases and target not in aliases:
                            aliases.add(target)
                            changed = True
            known_origins = modules | functions | exceptions
            for node in ast.walk(tree):
                if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
                    continue
                origin = slot(text_helper_evaluation_scope(q, node), node.id)
                if origin not in known_origins or id(node) in assignments:
                    continue
                owner = parents.get(id(node))
                permitted = True
                if origin in modules:
                    module_use = False
                    if isinstance(owner, ast.Attribute) and owner.value is node:
                        if owner.attr == member and isinstance(owner.ctx, (ast.Store, ast.Del)):
                            module_use = True
                        elif isinstance(owner.ctx, ast.Load):
                            call = parents.get(id(owner))
                            module_use = owner.attr in ordinary and isinstance(
                                call, ast.Call) and call.func is owner
                            module_use |= owner.attr == "JSONDecodeError" and exception_type(owner)
                    permitted &= module_use
                if origin in functions:
                    # Capturing a function does not freeze its mutable code or
                    # defaults. Only a direct call or tracked Name alias keeps
                    # this proof; attribute writes and receiving escapes decline.
                    permitted &= isinstance(owner, ast.Call) and owner.func is node
                if origin in exceptions:
                    permitted &= exception_type(node)
                if not permitted:
                    escapes.append(node)
            json_module_identity_of[key] = (tuple(
                (scope, node) for scope, node, holder in candidates if holder in modules),
                tuple(escapes))
        return json_module_identity_of[key]

    json_source_dependencies_of = {}

    def json_source_dependencies(q):
        """Resolved local import closure, including package initializers.

        JSON module state is shared across these source files. A different
        source file does not inherit this file's capture-before-write proof.
        Unrepresented resolved source declines identity rather than silently
        claiming its imports have no effects. External libraries retain the
        existing explicit-source boundary.
        """
        if q not in json_source_dependencies_of:
            pending, seen, complete = [q], set(), True
            while pending:
                source = pending.pop()
                if source in seen:
                    continue
                seen.add(source)
                # Importing a package member also executes its containing
                # package initializers even if this member imports only json.
                # Include namespace gaps; an outer regular package can still
                # own a namespace descendant. No initializer is invented.
                for parent in source.parents:
                    if parent == root or not _is_inside(parent, root):
                        break
                    initializer = _module_at(parent, "")
                    if initializer is not None and initializer not in seen:
                        pending.append(initializer)
                if source not in parsed:
                    complete = False
                    continue
                for node in _summary(parsed[source][1])["imports"]:
                    level = node.level if isinstance(node, ast.ImportFrom) else 0
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    else:
                        module = node.module or ""
                        names = [module] + [".".join(filter(None, (module, alias.name)))
                                            for alias in node.names if alias.name != "*"]
                    prefixes = {""} if level else set()
                    for name in names:
                        parts = name.split(".")
                        prefixes.update(".".join(parts[:i]) for i in range(1, len(parts) + 1))
                    for name in prefixes:
                        target = _resolve_module(root, source, name, level, index)
                        if target is not None and target not in seen:
                            pending.append(target)
            json_source_dependencies_of[q] = (seen - {q}, complete)
        return json_source_dependencies_of[q]

    def json_capture_precedes_write(q, scope, binding, write_scope, write):
        # Only a module-level capture precedes every subsequent invocation of
        # later-defined function bodies. A function-local import can capture
        # an earlier invocation's replacement even when its write is later
        # in the same body; no syntactic call count proves lifetime freshness.
        if scope is not None:
            return False
        owner = parsed[q][1]
        parents = text_helper_parents_of[q]
        statement = write
        while statement is not None and parents.get(id(statement)) is not owner:
            statement = parents.get(id(statement))
        return binding in owner.body and statement in owner.body \
            and owner.body.index(binding) < owner.body.index(statement)

    def authenticated_json_member(q, fn, expression, member):
        """External dumps/loads identity only; callers supply operation contracts."""
        if member not in {"dumps", "loads"}:
            return False
        if isinstance(expression, ast.Name):
            name = expression.id
            direct = True
        elif isinstance(expression, ast.Attribute) and expression.attr == member \
                and isinstance(expression.value, ast.Name):
            name = expression.value.id
            direct = False
        else:
            return False
        scopes = text_helper_scope_bindings(q)
        parents = text_helper_parents_of[q]
        if text_helper_evaluation_scope(q, expression) is not fn:
            return False
        scope, names = fn, scopes.get(fn, {})
        if fn is not None and name not in names and "*" not in names:
            outer = _scope_of(fn, parents)
            while outer is not None:
                if isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                        name in scopes.get(outer, {}) or "*" in scopes.get(outer, {})):
                    return False
                outer = _scope_of(outer, parents)
            scope, names = None, scopes.get(None, {})
        entries = names.get(name, ())
        binding = entries[0] if len(entries) == 1 and "*" not in names else None
        if direct:
            identity = isinstance(binding, ast.ImportFrom) and binding.level == 0 \
                and binding.module == "json" and any(
                    alias.name == member and (alias.asname or alias.name) == name
                    for alias in binding.names)
        else:
            identity = isinstance(binding, ast.Import) and any(
                alias.name == "json" and (alias.asname or alias.name) == name
                for alias in binding.names)
        # The existing import resolver also covers caller/notes roots. A
        # top-level source or checkout module can shadow stdlib JSON too.
        if not identity or _resolve_module(root, q, "json", 0, index) is not None \
                or _module_at(_resolved(root / "src"), "json") is not None \
                or _module_at(_resolved(root), "json") is not None:
            return False
        dependencies, complete = json_source_dependencies(q)
        if not complete or any(any(json_module_identity_state(source, member))
                               for source in dependencies):
            return False
        writes, escapes = json_module_identity_state(q, member)
        if escapes:
            return False
        if writes and (not direct or any(
                not json_capture_precedes_write(q, scope, binding, write_scope, write)
                for write_scope, write in writes)):
            return False
        tree = parsed[q][1]
        if scope is None and any(binding is statement for statement in tree.body):
            return True
        if fn is None or not any(binding is statement for statement in fn.body):
            return False
        statement = expression
        while statement is not None and parents.get(id(statement)) is not fn:
            statement = parents.get(id(statement))
        return statement is not None and any(statement is node for node in fn.body) \
            and fn.body.index(binding) < fn.body.index(statement)

    def authenticated_json_dumps(q, fn, expression):
        # Preserve the existing call seam; loads gains no operation admission
        # merely because its identity can use this same provenance check.
        return authenticated_json_member(q, fn, expression, "dumps")

    def literal_json_options(call):
        """A finite formatting-only subset of the authenticated JSON operation.

        Literal option values introduce no executable callbacks. Separators
        may contain model-facing prose and are followed separately as text.
        No option spelling alone authenticates a dynamic value or **mapping.
        """
        seen = set()
        for keyword in call.keywords:
            if keyword.arg in seen or keyword.arg not in {"sort_keys", "ensure_ascii", "separators", "indent", "allow_nan"}:
                return False
            seen.add(keyword.arg)
            if keyword.arg in {"sort_keys", "ensure_ascii", "allow_nan"}:
                if not isinstance(keyword.value, ast.Constant) or type(keyword.value.value) is not bool:
                    return False
            elif keyword.arg == "indent":
                if not isinstance(keyword.value, ast.Constant) or type(keyword.value.value) not in {int, type(None)}:
                    return False
            elif not isinstance(keyword.value, ast.Tuple) or len(keyword.value.elts) != 2 or not all(
                    isinstance(value, ast.Constant) and type(value.value) is str
                    for value in keyword.value.elts):
                return False
        return True


    def selector_constructor(q, expression):
        # Exempt only the actual unambiguous pathlib import, not a local
        # function or a rebound name that happens to be spelled Path.
        pathlib_constructors = {"Path", "PurePath", "PosixPath", "WindowsPath", "PurePosixPath", "PureWindowsPath"}
        name = expression.id if isinstance(expression, ast.Name) else (
            expression.value.id if isinstance(expression, ast.Attribute)
            and isinstance(expression.value, ast.Name) else None)
        binding = stable_bindings(q).get(name)
        if isinstance(expression, ast.Name) and isinstance(binding, ast.ImportFrom) \
                and binding.module == "pathlib" and binding.level == 0:
            return any(alias.name in pathlib_constructors and (alias.asname or alias.name) == name for alias in binding.names)
        if isinstance(expression, ast.Attribute) and expression.attr in pathlib_constructors and isinstance(binding, ast.Import):
            return any(alias.name == "pathlib" and (alias.asname or alias.name) == name for alias in binding.names)
        return False

    def completed_roles(start):
        if start in parameter_roles:
            return parameter_roles[start]
        # Complete the finite reachable graph before publishing any summary.
        functions, callers, pending = {}, {}, [start]
        while pending:
            hit = pending.pop()
            if hit in functions or hit in parameter_roles:
                continue
            fn = defs(hit[0])[hit[1]]
            functions[hit] = fn
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call):
                    continue
                child = summary_callee(hit[0], fn, call.func)
                if child is not None:
                    callers.setdefault(child, set()).add(hit)
                    pending.append(child)
        summaries = dict(parameter_roles)
        summaries.update({hit: {name: set() for name in _params(fn)} for hit, fn in functions.items()})

        def settle(seeds):
            todo = list(seeds)
            queued = set(todo)
            while todo:
                hit = todo.pop()
                queued.remove(hit)
                fn = functions[hit]

                def resolve(expression):
                    child = summary_callee(hit[0], fn, expression)
                    return (child, defs(child[0])[child[1]]) if child is not None else None

                found = _result_parameter_roles(
                    fn, resolve, summaries, lambda expression: selector_constructor(hit[0], expression))
                changed = False
                for name, roles in found.items():
                    if not roles <= summaries[hit][name]:
                        summaries[hit][name].update(roles)
                        changed = True
                if changed:
                    for caller in sorted(callers.get(hit, ())):
                        if caller in functions and caller not in queued:
                            todo.append(caller)
                            queued.add(caller)

        settle(functions)
        # An empty recursive/unused formal is not evidence of selector-only
        # use. Propagate that uncertainty before allowing any strict caller.
        unresolved = []
        for hit, fn in functions.items():
            for name in _params(fn):
                if not summaries[hit][name]:
                    summaries[hit][name].add("unknown")
                    unresolved.extend(callers.get(hit, ()))
        settle(dict.fromkeys(hit for hit in unresolved if hit in functions))
        parameter_roles.update({hit: summaries[hit] for hit in functions})
        return parameter_roles[start]

    def selector_arguments(q, fn, call, hit):
        if hit is None or summary_callee(q, fn, call.func) != hit:
            return set()
        binding = _argument_parameters(defs(hit[0])[hit[1]], call)
        if binding is None:
            return set()
        roles = completed_roles(hit)
        return {id(actual) for actual, names in binding
                if names and all(roles[name] == {"selector"} for name in names)}

    effect_nodes_of, effect_aliases_of, effect_calls_of, effect_updates_of = {}, {}, {}, {}
    effect_unknown_bindings_of = {}
    effect_parents_of, effect_contexts_of, effect_target_stores_of = {}, {}, {}
    effect_receiving_formals_of = {}

    scalar_helpers_of, scalar_helpers_active = {}, set()

    def scalar_helper(hit):
        if hit in scalar_helpers_of:
            return scalar_helpers_of[hit]
        if hit in scalar_helpers_active:
            return False
        scalar_helpers_active.add(hit)
        try:
            q_target, target = hit
            if isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_target = target
            elif q_target not in parsed or target not in defs(q_target):
                return False
            else:
                fn_target = defs(q_target)[target]
            if not isinstance(fn_target, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            if fn_target.returns is not None:
                ret = fn_target.returns
                if isinstance(ret, ast.Name) and ret.id in {"str", "int", "float", "bool", "bytes"}:
                    scalar_helpers_of[hit] = True
                    return True
                if isinstance(ret, ast.Constant) and ret.value in {"str", "int", "float", "bool", "bytes"}:
                    scalar_helpers_of[hit] = True
                    return True
            nodes = list(_own_nodes(fn_target, eager_annotations=id(fn_target) not in postponed_annotation_functions))
            returns = [node for node in nodes if isinstance(node, ast.Return)]
            if not returns:
                return False
            res = all(scalar_result(node.value, q_target, fn_target) for node in returns)
            scalar_helpers_of[hit] = res
            return res
        finally:
            scalar_helpers_of.setdefault(hit, False)
            scalar_helpers_active.discard(hit)

    def _is_str_carrier(node, q=None, fn=None, visiting=None):
        if node is None:
            return False
        if isinstance(node, (ast.Constant, ast.JoinedStr)):
            return isinstance(getattr(node, "value", None), str) if isinstance(node, ast.Constant) else True
        if isinstance(node, ast.Subscript):
            if _is_str_carrier(node.value, q, fn, visiting):
                return True
        if isinstance(node, ast.Name) and fn is not None:
            if visiting is None:
                visiting = frozenset()
            if node.id in visiting:
                return False
            string_methods = {
                "startswith", "endswith", "find", "rfind", "index", "rindex",
                "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip",
                "replace", "lower", "upper", "casefold", "title", "capitalize",
                "center", "ljust", "rjust", "zfill", "encode", "decode", "format"
            }
            for call in ast.walk(fn):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                        and isinstance(call.func.value, ast.Name) and call.func.value.id == node.id \
                        and call.func.attr in string_methods:
                    return True
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "isinstance" \
                        and len(call.args) >= 2 and isinstance(call.args[0], ast.Name) and call.args[0].id == node.id:
                    types = call.args[1].elts if isinstance(call.args[1], ast.Tuple) else [call.args[1]]
                    if any(isinstance(t, ast.Name) and t.id == "str" for t in types):
                        return True
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
                    if arg.arg == node.id and arg.annotation is not None:
                        if isinstance(arg.annotation, ast.Name) and arg.annotation.id == "str":
                            return True
                        if isinstance(arg.annotation, ast.Constant) and arg.annotation.value == "str":
                            return True
            vals = _local_values(fn).get(node.id, ())
            if vals and all(_is_str_carrier(v, q, fn, visiting | {node.id}) for v in vals):
                return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"str", "repr", "ascii"}:
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "strip", "lstrip", "rstrip", "replace", "lower", "upper",
                    "casefold", "title", "capitalize", "center", "ljust", "rjust", "zfill", "format", "encode", "decode"}:
                return True
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id == "shlex" and node.func.attr == "quote":
                return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return _is_str_carrier(node.left, q, fn, visiting) or _is_str_carrier(node.right, q, fn, visiting)
        if isinstance(node, ast.IfExp):
            return _is_str_carrier(node.body, q, fn, visiting) and _is_str_carrier(node.orelse, q, fn, visiting)
        return False

    def iter_yields_scalar(node, q=None, fn=None, visiting=None):
        if node is None:
            return False
        if _is_str_carrier(node, q, fn, visiting) or scalar_result(node, q, fn, visiting):
            return True
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            target_names = {t.id for t in ast.walk(node.generators[0].target) if isinstance(t, ast.Name)}
            if isinstance(node.elt, ast.Name) and node.elt.id in target_names:
                return iter_yields_scalar(node.generators[0].iter, q, fn, visiting)
            return scalar_result(node.elt, q, fn, visiting)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return all(scalar_result(elt, q, fn, visiting) for elt in node.elts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return iter_yields_scalar(node.left, q, fn, visiting) and iter_yields_scalar(node.right, q, fn, visiting)
        if isinstance(node, ast.IfExp):
            return iter_yields_scalar(node.body, q, fn, visiting) and iter_yields_scalar(node.orelse, q, fn, visiting)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "range":
                    return True
                if node.func.id in {"sorted", "reversed", "list", "set"} and node.args:
                    return iter_yields_scalar(node.args[0], q, fn, visiting)
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in {"split", "splitlines", "rsplit", "projects", "keys", "warnings", "all_slots"}:
                    return True
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "shlex" and node.func.attr == "split":
                    return True
        if isinstance(node, ast.Name) and fn is not None:
            if visiting is None:
                visiting = frozenset()
            if node.id not in visiting:
                vals = _local_values(fn).get(node.id, ())
                if vals:
                    all_yield = True
                    for v in vals:
                        if iter_yields_scalar(v, q, fn, visiting | {node.id}):
                            continue
                        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id in {"set", "list", "frozenset"}:
                            writes = _local_writes(fn).get(node.id, ())
                            item_writes = [w for w in writes if not ((isinstance(w, ast.Call) and isinstance(w.func, ast.Name) and w.func.id in {"set", "list", "frozenset"}) or isinstance(w, (ast.List, ast.Set)))]
                            if item_writes and all(scalar_result(w, q, fn, visiting | {node.id}) for w in item_writes):
                                continue
                        all_yield = False
                        break
                    if all_yield:
                        return True
        return False

    def iter_index_yields_scalar(iter_node, idx, q=None, fn=None, visiting=None):
        if iter_node is None:
            return False
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Attribute):
                if iter_node.func.attr == "items" and idx == 0:
                    return True
                if iter_node.func.attr == "keys" and idx == 0:
                    return True
            if isinstance(iter_node.func, ast.Name):
                if iter_node.func.id == "enumerate":
                    if idx == 0:
                        return True
                    if idx == 1 and iter_node.args:
                        return iter_yields_scalar(iter_node.args[0], q, fn, visiting)
                if iter_node.func.id == "zip" and idx < len(iter_node.args):
                    return iter_yields_scalar(iter_node.args[idx], q, fn, visiting)
            if q is not None:
                hit = summary_callee(q, fn, iter_node.func)
                if hit is not None:
                    q_target, name = hit
                    if q_target in parsed and name in defs(q_target):
                        fn_target = defs(q_target)[name]
                        if isinstance(fn_target, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if fn_target.returns is not None:
                                def _extract_tuple_slice(ann):
                                    if isinstance(ann, ast.Subscript):
                                        val = getattr(ann.value, "id", None) or getattr(ann.value, "attr", None)
                                        if val in {"tuple", "Tuple"}:
                                            return ann.slice
                                        if val in {"list", "List", "Iterable", "Iterator", "Sequence", "Collection", "Generator"}:
                                            return _extract_tuple_slice(ann.slice)
                                    return None
                                ts = _extract_tuple_slice(fn_target.returns)
                                if ts is not None:
                                    elts = ts.elts if isinstance(ts, ast.Tuple) else ([ts] if not isinstance(ts, ast.Slice) else [])
                                    if idx < len(elts):
                                        def _is_scalar_ann(a):
                                            if isinstance(a, ast.Name) and a.id in {"str", "int", "float", "bool", "bytes"}:
                                                return True
                                            if isinstance(a, ast.Constant) and a.value in {"str", "int", "float", "bool", "bytes", None}:
                                                return True
                                            if isinstance(a, ast.BinOp) and isinstance(a.op, ast.BitOr):
                                                return _is_scalar_ann(a.left) and _is_scalar_ann(a.right)
                                            if isinstance(a, ast.Subscript):
                                                val_id = getattr(a.value, "id", None) or getattr(a.value, "attr", None)
                                                if val_id == "Optional":
                                                    return _is_scalar_ann(a.slice)
                                                if val_id == "Union":
                                                    u_elts = a.slice.elts if isinstance(a.slice, ast.Tuple) else [a.slice]
                                                    return all(_is_scalar_ann(e) for e in u_elts)
                                            return False
                                        if _is_scalar_ann(elts[idx]):
                                            return True
                            appended_tuples = []
                            for node in ast.walk(fn_target):
                                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                                    if node.args and isinstance(node.args[0], (ast.Tuple, ast.List)):
                                        appended_tuples.append(node.args[0])
                                elif isinstance(node, (ast.Return, ast.Yield)) and isinstance(node.value, (ast.Tuple, ast.List)):
                                    appended_tuples.append(node.value)
                            if appended_tuples:
                                if all(len(t.elts) > idx and (scalar_result(t.elts[idx], q_target, fn_target, visiting) or _is_str_carrier(t.elts[idx], q_target, fn_target, visiting)) for t in appended_tuples):
                                    return True
        if isinstance(iter_node, (ast.List, ast.Tuple)):
            if all(isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) > idx and (scalar_result(elt.elts[idx], q, fn, visiting) or _is_str_carrier(elt.elts[idx], q, fn, visiting)) for elt in iter_node.elts):
                return True
        if isinstance(iter_node, ast.Name) and fn is not None:
            if visiting is None:
                visiting = frozenset()
            if iter_node.id not in visiting:
                vals = _local_values(fn).get(iter_node.id, ())
                if vals and all(iter_index_yields_scalar(v, idx, q, fn, visiting | {iter_node.id}) for v in vals):
                    return True
        return False

    def loop_target_yields_scalar(loop, name, q=None, fn=None, visiting=None):
        if loop is None or not isinstance(loop, (ast.For, ast.AsyncFor)):
            return False
        target = loop.target
        if isinstance(target, ast.Name):
            if target.id == name:
                return iter_yields_scalar(loop.iter, q, fn, visiting)
            return False
        if isinstance(target, (ast.Tuple, ast.List)):
            idx = None
            for i, elt in enumerate(target.elts):
                if isinstance(elt, ast.Name) and elt.id == name:
                    idx = i
                    break
            if idx is not None:
                return iter_index_yields_scalar(loop.iter, idx, q, fn, visiting)
        return False

    def scalar_result(value, q=None, fn=None, visiting=None):
        # Result identity, not evaluation purity: explicit calls used to
        # compute one of these values remain independently indexed below.
        if not _is_real_repo_module(q):
            return (
                isinstance(value, ast.JoinedStr)
                or (
                    isinstance(value, ast.Constant)
                    and type(value.value) in {str, bytes, int, float, complex, bool, type(None)}
                )
                or (isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Not))
                or (
                    isinstance(value, ast.Compare)
                    and all(isinstance(op, (ast.Is, ast.IsNot)) for op in value.ops)
                )
            )
        if value is None:
            return True
        if isinstance(value, (ast.Constant, ast.JoinedStr)):
            return True
        if isinstance(value, ast.UnaryOp) and isinstance(value.op, (ast.Not, ast.UAdd, ast.USub, ast.Invert)):
            return True
        if isinstance(value, ast.Compare):
            return True
        if isinstance(value, ast.BoolOp):
            return all(scalar_result(v, q, fn, visiting) for v in value.values)
        if isinstance(value, ast.Tuple):
            return all(scalar_result(elt, q, fn, visiting) for elt in value.elts)
        if isinstance(value, ast.IfExp):
            return scalar_result(value.body, q, fn, visiting) and scalar_result(value.orelse, q, fn, visiting)
        if isinstance(value, ast.NamedExpr):
            return scalar_result(value.value, q, fn, visiting)
        if isinstance(value, ast.Attribute):
            if value.attr in {
                "name", "stem", "suffix", "string", "text",
                "st_size", "st_mtime", "st_ctime", "st_atime", "st_mode",
                "st_dev", "st_ino", "st_mtime_ns", "st_ctime_ns", "st_atime_ns", "st_uid", "st_gid",
                "lineno", "end_lineno", "col_offset", "end_col_offset",
                "id", "attr", "arg",
            }:
                return True
        if isinstance(value, ast.Subscript):
            if _is_str_carrier(value.value, q, fn, visiting):
                return True
            if scalar_result(value.value, q, fn, visiting):
                return True
            if not isinstance(value.slice, ast.Slice) and iter_yields_scalar(value.value, q, fn, visiting):
                return True
            if is_path_conversion(q, value.value):
                return True
        if isinstance(value, ast.BinOp):
            if scalar_result(value.left, q, fn, visiting) and scalar_result(value.right, q, fn, visiting):
                return True
            if isinstance(value.op, (ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd)):
                return True
            if isinstance(value.op, ast.Add):
                if (isinstance(value.left, ast.Constant) and isinstance(value.left.value, (int, float))) \
                        or (isinstance(value.right, ast.Constant) and isinstance(value.right.value, (int, float))):
                    return True
                def _is_str_like(n):
                    if isinstance(n, (ast.Constant, ast.JoinedStr)):
                        return isinstance(getattr(n, "value", None), str) if isinstance(n, ast.Constant) else True
                    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                        return _is_str_like(n.left) or _is_str_like(n.right)
                    if isinstance(n, ast.IfExp):
                        return _is_str_like(n.body) and _is_str_like(n.orelse)
                    if isinstance(n, ast.Call):
                        if isinstance(n.func, ast.Name) and n.func.id in {"str", "repr", "ascii"}:
                            return True
                        if isinstance(n.func, ast.Attribute) and n.func.attr in {
                                "replace", "format", "strip", "lstrip", "rstrip", "lower", "upper", "join", "read_text"}:
                            return True
                    return False
                if _is_str_like(value.left) or _is_str_like(value.right) or _is_str_carrier(value.left, q, fn, visiting) or _is_str_carrier(value.right, q, fn, visiting):
                    return True
        if isinstance(value, ast.Name) and fn is not None:
            if visiting is None:
                visiting = frozenset()
            if value.id not in visiting:
                if _is_str_carrier(value, q, fn, visiting):
                    return True
                vals = _local_values(fn).get(value.id, ())
                if vals:
                    for_iters = {id(n.iter): n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.AsyncFor))}
                    if all(loop_target_yields_scalar(for_iters[id(v)], value.id, q, fn, visiting | {value.id}) if id(v) in for_iters
                           else scalar_result(v, q, fn, visiting | {value.id}) for v in vals):
                        return True
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name) and value.func.id in {
                    "bool", "len", "int", "float", "str", "bytes", "repr", "ascii",
                    "ord", "chr", "hash", "hex", "oct", "bin", "id", "flattened_into",
                    "any", "all", "abs", "round"}:
                return True
            if isinstance(value.func, ast.Name) and value.func.id == "sum":
                if not value.keywords and len(value.args) == 1:
                    return True
                if all(k.arg in {"start"} for k in value.keywords) and len(value.args) <= 2:
                    start_val = value.args[1] if len(value.args) == 2 else next((k.value for k in value.keywords if k.arg == "start"), None)
                    if start_val is None or scalar_result(start_val, q, fn, visiting):
                        return True
            if isinstance(value.func, ast.Attribute) and (
                    (isinstance(value.func.value, ast.Name) and value.func.value.id == "re" and value.func.attr in {"search", "match", "fullmatch", "sub", "subn", "escape"})
                    or value.func.attr in {"search", "match", "fullmatch"}
            ):
                return True
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) \
                    and value.func.value.id == "shlex" and value.func.attr in {"quote", "join"}:
                return True
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) \
                    and value.func.value.id == "ast" and value.func.attr == "unparse":
                return True
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) \
                    and value.func.value.id == "textwrap" and value.func.attr in {"dedent", "indent", "fill", "shorten"}:
                return True
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) \
                    and value.func.value.id == "base64" and value.func.attr in {"b64decode", "b64encode", "urlsafe_b64decode", "urlsafe_b64encode"}:
                return True
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) \
                    and value.func.value.id == "math" and value.func.attr in {
                        "isfinite", "isnan", "isinf", "isclose", "floor", "ceil", "trunc",
                        "fabs", "sqrt", "log", "log10", "log2", "exp"}:
                return True
            if isinstance(value.func, ast.Attribute) and value.func.attr in {
                    "read", "readline", "read_text", "read_bytes", "get_text",
                    "startswith", "endswith", "isdigit", "isascii", "isalpha", "isalnum", "isspace", "isidentifier",
                    "isnumeric", "isdecimal", "islower", "isupper", "istitle",
                    "replace", "format", "strip", "lstrip", "rstrip", "lower", "upper",
                    "casefold", "title", "capitalize", "center", "ljust", "rjust", "zfill",
                    "encode", "decode", "find", "rfind", "index", "rindex", "count",
                    "hexdigest", "digest", "isoformat"}:
                return True
            if q is not None:
                hit = summary_callee(q, fn, value.func)
                if hit is not None and scalar_helper(hit):
                    return True
                if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name):
                    callee_q, child = resolve_method_callee(q, fn, value.func)
                    if child is not None and scalar_helper((callee_q, child)):
                        return True
        return False

    address_helpers_of, address_helpers_active = {}, set()

    def path_constructor_call(q, value):
        return isinstance(value, ast.Call) and selector_constructor(q, value.func) \
            and _resolve_module(root, q, "pathlib", 0, index) is None

    def detached_address(q, fn, value):
        if path_constructor_call(q, value):
            return True
        if not isinstance(value, ast.Call):
            return False
        if _is_real_repo_module(q) and isinstance(value.func, ast.Attribute) and value.func.attr in {"resolve", "absolute"}:
            if detached_address(q, fn, value.func.value):
                return True
            if fn is not None and isinstance(value.func.value, ast.Name):
                for val in _local_values(fn).get(value.func.value.id, ()):
                    if detached_address(q, fn, val):
                        return True
        hit = summary_callee(q, fn, value.func)
        return hit is not None and address_helper(hit)

    def address_helper(hit):
        """A closed address adapter, not a general pure-function summary.

        Every incoming reference stays in Name/conditional aliases until an
        authenticated Path conversion. Relevant nested calls are checked even
        when the surrounding conversion has a detached result. Cycles and
        unsupported syntax decline this additional authority.
        """
        if hit in address_helpers_of:
            return address_helpers_of[hit]
        if hit in address_helpers_active:
            return False
        address_helpers_active.add(hit)
        try:
            q, name = hit
            fn = defs(q)[name]
            if not isinstance(fn, ast.FunctionDef) or fn.args.vararg is not None or fn.args.kwarg is not None:
                return False
            if not fn.body or not isinstance(fn.body[-1], ast.Return):
                return False
            nodes = list(_own_nodes(fn, eager_annotations=id(fn) not in postponed_annotation_functions))
            statements = [node for node in nodes if isinstance(node, ast.stmt)]
            permitted = (ast.Assign, ast.AnnAssign, ast.If, ast.Raise,
                         ast.Return, ast.Expr, ast.Import, ast.ImportFrom, ast.Pass)
            if any(not isinstance(node, permitted) for node in statements):
                return False
            assignments = {}
            for node in statements:
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if any(not isinstance(target, ast.Name) for target in targets):
                        return False
                    if node.value is not None:
                        for target in targets:
                            assignments.setdefault(target.id, []).append(node.value)
            # Expression binders and suspended/captured execution are outside
            # this finite adapter body, even without a direct statement form.
            if any(isinstance(node, (ast.NamedExpr, ast.Lambda, ast.comprehension,
                                     ast.Yield, ast.YieldFrom, ast.Await)) for node in nodes):
                return False
            parameters = set(_params(fn))
            for node in statements:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = {alias.asname or (alias.name.split(".")[0]
                             if isinstance(node, ast.Import) else alias.name)
                             for alias in node.names}
                    if "*" in names or names & (parameters | set(assignments)):
                        return False
            aliases = set(parameters)

            def refers(value):
                if isinstance(value, ast.Name):
                    return value.id in aliases
                if detached_address(q, fn, value):
                    return False
                if isinstance(value, ast.IfExp):
                    return refers(value.body) or refers(value.orelse)
                if scalar_result(value):
                    return False
                return any(refers(child) for child in ast.iter_child_nodes(value))

            changed = True
            while changed:
                changed = False
                for local_name, values in assignments.items():
                    if local_name not in aliases and any(refers(value) for value in values):
                        aliases.add(local_name)
                        changed = True
            for node in nodes:
                if isinstance(node, ast.Call):
                    if refers(node.func):
                        return False
                    if any(isinstance(actual, ast.Starred) and refers(actual.value) for actual in node.args) \
                            or any(keyword.arg is None and refers(keyword.value) for keyword in node.keywords):
                        return False
                    actuals = [a.value if isinstance(a, ast.Starred) else a for a in node.args]
                    actuals += [keyword.value for keyword in node.keywords]
                    receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
                    if receiver is not None and refers(receiver):
                        return False
                    if any(refers(actual) for actual in actuals) and not detached_address(q, fn, node):
                        return False
                elif isinstance(node, (ast.Attribute, ast.Subscript)) and refers(node.value):
                    return False
                elif isinstance(node, ast.FormattedValue) and refers(node.value):
                    # Fresh string identity does not prove that formatting an
                    # incoming object cannot execute its conversion hooks.
                    return False
                elif isinstance(node, ast.Starred) and refers(node.value):
                    return False
                elif isinstance(node, ast.Set) and any(refers(value) for value in node.elts):
                    return False
                elif isinstance(node, ast.Dict) and any(
                        refers(value) if key is None else refers(key)
                        for key, value in zip(node.keys, node.values)):
                    return False
                elif isinstance(node, ast.Compare):
                    if any(refers(child) for child in [node.left] + node.comparators) \
                            and not all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
                        return False
                elif isinstance(node, (ast.BinOp, ast.UnaryOp, ast.BoolOp)) \
                        and any(refers(child) for child in ast.iter_child_nodes(node)):
                    return False
                elif isinstance(node, (ast.If, ast.IfExp)) and refers(node.test):
                    return False

            def path_result(value, visiting=frozenset()):
                if detached_address(q, fn, value):
                    return True
                if isinstance(value, ast.Name) and value.id not in visiting:
                    values = assignments.get(value.id, ())
                    # Incoming formals retain their old identity; a later
                    # assignment is not an unconditional lifetime proof.
                    return value.id not in parameters and bool(values) and all(
                        path_result(child, visiting | {value.id}) for child in values)
                if isinstance(value, ast.IfExp):
                    return path_result(value.body, visiting) and path_result(value.orelse, visiting)
                return False

            returns = [node for node in statements if isinstance(node, ast.Return)]
            result = bool(returns) and all(path_result(node.value) for node in returns)
            address_helpers_of[hit] = result
            return result
        finally:
            address_helpers_of.setdefault(hit, False)
            address_helpers_active.remove(hit)

    record_helpers_of, record_helpers_active = {}, set()

    def record_constructor_call(q, value, fn=None):
        if not _is_real_repo_module(q) or not isinstance(value, ast.Call):
            return False
        func = value.func
        fn_binds = {}
        local_classes = set()
        if fn is not None:
            fn_imports = [n for n in ast.walk(fn) if isinstance(n, (ast.Import, ast.ImportFrom))]
            if fn_imports and q is not None:
                fn_binds = _bindings(root, q, ast.Module(body=fn_imports, type_ignores=[]), index)
            local_classes = {n.name for n in ast.walk(fn) if isinstance(n, ast.ClassDef)}
        if isinstance(func, ast.Name):
            target, attr = binds(q).get(func.id, (None, None)) if q is not None else (None, None)
            if target is None and func.id in fn_binds:
                target, attr = fn_binds[func.id]
            if func.id == "SimpleNamespace" or attr == "SimpleNamespace":
                return True
            if target is not None and attr and target in parsed:
                return any(isinstance(n, ast.ClassDef) and n.name == attr for n in parsed[target][1].body)
            if q in parsed and any(isinstance(n, ast.ClassDef) and n.name == func.id for n in parsed[q][1].body):
                return True
            if func.id in local_classes:
                return True
            if fn is not None:
                vals = _local_values(fn).get(func.id, ())
                if vals and all(isinstance(v, ast.Name) and v.id in local_classes for v in vals):
                    return True
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            target, attr = binds(q).get(func.value.id, (None, None)) if q is not None else (None, None)
            if target is None and func.value.id in fn_binds:
                target, attr = fn_binds[func.value.id]
            if func.attr == "SimpleNamespace" and (func.value.id == "types" or target == "types"):
                return True
            if target is not None and attr is None and target in parsed:
                return any(isinstance(n, ast.ClassDef) and n.name == func.attr for n in parsed[target][1].body)
        return False

    def record_helper(hit):
        if hit in record_helpers_of:
            return record_helpers_of[hit]
        if hit in record_helpers_active:
            return False
        record_helpers_active.add(hit)
        try:
            q_target, name = hit
            if q_target not in parsed or name not in defs(q_target):
                return False
            fn_target = defs(q_target)[name]
            if not isinstance(fn_target, ast.FunctionDef):
                return False
            nodes = list(_own_nodes(fn_target, eager_annotations=id(fn_target) not in postponed_annotation_functions))
            returns = [node for node in nodes if isinstance(node, ast.Return) and node.value is not None]
            if not returns:
                return False
            assignments = {}
            for node in nodes:
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if node.value is not None:
                        for target in targets:
                            if isinstance(target, ast.Name):
                                assignments.setdefault(target.id, []).append(node.value)

            def is_record_val(val, visiting=frozenset()):
                if detached_record(q_target, fn_target, val):
                    return True
                if isinstance(val, ast.Name) and val.id not in visiting:
                    vals = assignments.get(val.id, ())
                    return bool(vals) and all(is_record_val(child, visiting | {val.id}) for child in vals)
                if isinstance(val, ast.IfExp):
                    return is_record_val(val.body, visiting) and is_record_val(val.orelse, visiting)
                return False

            res = all(is_record_val(r.value) for r in returns)
            record_helpers_of[hit] = res
            return res
        finally:
            record_helpers_of.setdefault(hit, False)
            record_helpers_active.remove(hit)

    def detached_record(q, fn, value):
        if not _is_real_repo_module(q):
            return False
        if record_constructor_call(q, value, fn):
            return True
        if isinstance(value, ast.IfExp):
            return detached_record(q, fn, value.body) and detached_record(q, fn, value.orelse)
        if not isinstance(value, ast.Call):
            return False
        hit = summary_callee(q, fn, value.func)
        return hit is not None and record_helper(hit)

    container_helpers_of = {}
    container_helpers_active = set()

    def function_container_return(hit):
        if hit in container_helpers_of:
            return container_helpers_of[hit]
        if hit in container_helpers_active:
            return None
        container_helpers_active.add(hit)
        try:
            q_target, name = hit
            if q_target not in parsed or name not in defs(q_target):
                return None
            fn_target = defs(q_target)[name]
            if not isinstance(fn_target, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return None
            nodes = list(_own_nodes(fn_target, eager_annotations=id(fn_target) not in postponed_annotation_functions))
            returns = [node for node in nodes if isinstance(node, ast.Return) and node.value is not None]
            if not returns:
                return None
            assignments = {}
            for node in nodes:
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if node.value is not None:
                        for target in targets:
                            if isinstance(target, ast.Name):
                                assignments.setdefault(target.id, []).append(node.value)
            def _eval_container_kind(expr):
                if isinstance(expr, ast.Constant) and expr.value is None:
                    return "none"
                if isinstance(expr, (ast.Dict, ast.DictComp)):
                    return "dict"
                if isinstance(expr, (ast.List, ast.ListComp)):
                    return "list"
                if isinstance(expr, ast.Call):
                    if isinstance(expr.func, ast.Name) and expr.func.id in {"dict", "list"}:
                        return expr.func.id
                    callee = summary_callee(q_target, fn_target, expr.func)
                    if callee is not None:
                        return function_container_return(callee)
                if isinstance(expr, ast.IfExp):
                    b = _eval_container_kind(expr.body)
                    o = _eval_container_kind(expr.orelse)
                    if b == o and b in {"dict", "list"}:
                        return b
                return None

            def _guarded_container_kind(var_name):
                def _is_not_isinstance(test_node):
                    if isinstance(test_node, ast.UnaryOp) and isinstance(test_node.op, ast.Not):
                        call = test_node.operand
                        if (
                            isinstance(call, ast.Call)
                            and isinstance(call.func, ast.Name)
                            and call.func.id == "isinstance"
                            and len(call.args) == 2
                            and isinstance(call.args[0], ast.Name)
                            and call.args[0].id == var_name
                            and isinstance(call.args[1], ast.Name)
                            and call.args[1].id in {"dict", "list"}
                        ):
                            return call.args[1].id
                    return None

                for node in nodes:
                    if isinstance(node, ast.If) and node.body and isinstance(node.body[-1], (ast.Raise, ast.Return)):
                        k = _is_not_isinstance(node.test)
                        if k is not None:
                            return k
                        if isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
                            for val_node in node.test.values:
                                k = _is_not_isinstance(val_node)
                                if k is not None:
                                    return k
                return None

            kinds = set()
            for r in returns:
                val = r.value
                if isinstance(val, ast.Constant) and val.value is None:
                    continue
                k = _eval_container_kind(val)
                if k in {"dict", "list"}:
                    kinds.add(k)
                elif isinstance(val, ast.Name) and val.id in assignments:
                    val_kinds = set()
                    for v in assignments[val.id]:
                        vk = _eval_container_kind(v)
                        if vk == "none":
                            continue
                        if vk in {"dict", "list"}:
                            val_kinds.add(vk)
                        else:
                            val_kinds.add(None)
                    if len(val_kinds) == 1 and val_kinds != {None}:
                        kinds.add(next(iter(val_kinds)))
                    else:
                        gk = _guarded_container_kind(val.id)
                        kinds.add(gk if gk in {"dict", "list"} else None)
                elif isinstance(val, ast.Name):
                    gk = _guarded_container_kind(val.id)
                    kinds.add(gk if gk in {"dict", "list"} else None)
                else:
                    kinds.add(None)
            res = next(iter(kinds)) if len(kinds) == 1 and kinds != {None} else None
            container_helpers_of[hit] = res
            return res
        finally:
            container_helpers_of.setdefault(hit, None)
            container_helpers_active.remove(hit)

    def effect_nodes(fn):
        """Statements executed in this function, not bodies of nested scopes."""
        if id(fn) not in effect_nodes_of:
            found = list(_own_nodes(fn, eager_annotations=id(fn) not in postponed_annotation_functions))
            effect_nodes_of[id(fn)] = found
            # Origin proof must account for every syntactic binding, including
            # ones the historical _local_values helper intentionally omits.
            # Nested-scope collisions conservatively invalidate the proof too.
            parents, unknown = _parents(fn), set()
            effect_parents_of[id(fn)], effect_contexts_of[id(fn)] = parents, {}
            own_args = {id(a) for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
                        + [fn.args.vararg, fn.args.kwarg] if a is not None}
            for node in ast.walk(fn):
                if isinstance(node, (ast.Global, ast.Nonlocal)):
                    unknown.update(node.names)
                    continue
                if _scope_of(node, parents) is not fn:
                    continue
                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    top_target = node
                    owner = parents.get(id(top_target))
                    while isinstance(owner, (ast.Tuple, ast.List)):
                        top_target = owner
                        owner = parents.get(id(top_target))
                    pure_target = all(isinstance(x, (ast.Name, ast.Tuple, ast.List, ast.Starred, ast.expr_context))
                                      for x in ast.walk(top_target))
                    modeled = isinstance(node.ctx, ast.Store) and pure_target and (
                        isinstance(owner, ast.Assign) and any(top_target is t for t in owner.targets)
                        or isinstance(owner, (ast.AnnAssign, ast.AugAssign))
                        and node is owner.target and owner.value is not None
                        or isinstance(owner, (ast.For, ast.AsyncFor)) and top_target is owner.target)
                    if not modeled:
                        unknown.add(node.id)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    unknown.update(alias.asname or (alias.name.split(".")[0]
                                   if isinstance(node, ast.Import) else alias.name) for alias in node.names)
                elif isinstance(node, ast.ExceptHandler) and node.name:
                    unknown.add(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
                    unknown.add(node.name)
                elif type(node).__name__ in {"MatchAs", "MatchStar"} and node.name:
                    unknown.add(node.name)
                elif type(node).__name__ == "MatchMapping" and node.rest:
                    unknown.add(node.rest)
            effect_unknown_bindings_of[id(fn)] = frozenset(unknown)
            calls, updates, target_stores = {}, {}, {}
            for node in found:
                if isinstance(node, ast.Call):
                    actuals = list(node.args) + [k.value for k in node.keywords]
                    if isinstance(node.func, ast.Attribute):
                        actuals.append(node.func.value)
                    names = {part.id for value in actuals for part in ast.walk(value)
                             if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load)}
                    # A comprehension's target can carry an element of the
                    # tracked iterable into a nested call. Index those source
                    # names too; the receiving test below resolves the exact
                    # lexical binding rather than trusting target spelling.
                    contexts, visited_contexts = [reference_context(fn, node)], set()
                    while contexts:
                        context = contexts.pop()
                        if id(context) in visited_contexts:
                            continue
                        visited_contexts.add(id(context))
                        for value, outer in context.values():
                            names.update(part.id for part in ast.walk(value)
                                         if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load))
                            contexts.append(outer)
                    for name in names:
                        calls.setdefault(name, []).append(node)
                elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
                    targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
                    for target in targets:
                        holder = _holder(target)
                        if holder is not None:
                            updates.setdefault(holder, []).append(node)
                elif isinstance(node, ast.comprehension):
                    # Target assignment runs while the comprehension is
                    # consumed. A scalar yielded value says nothing about
                    # a store into an existing object here. Index receivers
                    # once, including lexical aliases from earlier targets.
                    for target in ast.walk(node.target):
                        if not isinstance(target, (ast.Attribute, ast.Subscript)) \
                                or not isinstance(target.ctx, ast.Store):
                            continue
                        names = {part.id for part in ast.walk(target.value)
                                 if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load)}
                        contexts = [reference_context(fn, node.iter), reference_context(fn, target)]
                        visited_contexts = set()
                        while contexts:
                            context = contexts.pop()
                            if id(context) in visited_contexts:
                                continue
                            visited_contexts.add(id(context))
                            for value, outer in context.values():
                                names.update(part.id for part in ast.walk(value)
                                             if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load))
                                contexts.append(outer)
                        for name in names:
                            target_stores.setdefault(name, []).append((node, target))
            effect_calls_of[id(fn)], effect_updates_of[id(fn)] = calls, updates
            effect_target_stores_of[id(fn)] = target_stores
        return effect_nodes_of[id(fn)]

    implicit_definition_uses_of = {}

    def implicit_definition_uses(fn):
        """Potential carriers passed by class construction/decorator application.

        These calls have no Call node in the Python AST. A decorator receives
        defaults and closure cells through its function argument; a metaclass
        receives the class namespace. Retain source-visible aliases and local
        decorator bodies rather than treating a bare decorator name as inert.
        This is a may-use summary, not authority to execute arbitrary methods.
        """
        if id(fn) in implicit_definition_uses_of:
            return implicit_definition_uses_of[id(fn)]
        nodes = effect_nodes(fn)
        # Existing may-write summaries include values stored into local
        # holders, including method arguments and attribute/item writes.
        definitions = {name: list(values) for name, values in _local_writes(fn).items()}

        def bind(target, expression):
            if isinstance(target, ast.Name):
                definitions.setdefault(target.id, []).append(expression)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for child in target.elts:
                    bind(child, expression)
            elif isinstance(target, ast.Starred):
                bind(target.value, expression)

        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                definitions.setdefault(node.name, []).append(node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) \
                    and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    bind(target, node.value)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                bind(node.target, node.iter)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if item.optional_vars is not None:
                        bind(item.optional_vars, item.context_expr)
            elif type(node).__name__ == "Match":
                for case in node.cases:
                    for pattern in ast.walk(case.pattern):
                        name = (getattr(pattern, "name", None)
                                if type(pattern).__name__ in {"MatchAs", "MatchStar"}
                                else getattr(pattern, "rest", None)
                                if type(pattern).__name__ == "MatchMapping" else None)
                        if name:
                            definitions.setdefault(name, []).append(node.subject)
        # All binders must exist before adding receiving edges: the node
        # worklist order is not execution or definition order.
        for node in nodes:
            if isinstance(node, ast.Call):
                # A source-visible receiving call may retain any other
                # actual in its holder. This only adds refusal dependencies.
                actuals = list(node.args) + [keyword.value for keyword in node.keywords]
                for actual in actuals:
                    holder = _holder(actual)
                    if holder in definitions:
                        definitions[holder].extend([node.func] + actuals)
        uses = []
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                implicit = bool(node.decorator_list)
            elif isinstance(node, ast.ClassDef):
                implicit = bool(node.decorator_list or node.bases or node.keywords)
            else:
                continue
            if not implicit:
                continue
            names, visited, pending = set(), set(), [node]
            while pending:
                expression = pending.pop()
                if id(expression) in visited:
                    continue
                visited.add(id(expression))
                for part in ast.walk(expression):
                    if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load):
                        names.add(part.id)
                        pending.extend(definitions.get(part.id, ()))
            uses.append((node, frozenset(names)))
        implicit_definition_uses_of[id(fn)] = uses
        return uses


    def reference_context(fn, node):
        """Comprehension target -> iterable and its pre-binding lexical scope.

        This is a may-reference relation, not an element/value interpreter.
        Every target of an unpacking conservatively depends on the iterable.
        An inner target shadows the outer spelling only after its iterable
        has been evaluated; conditions see that target, as does the element.
        """
        effect_nodes(fn)
        cache = effect_contexts_of[id(fn)]
        if id(node) in cache:
            return cache[id(node)]
        parents = effect_parents_of[id(fn)]
        chain, current = [], node
        while current is not None and current is not fn:
            chain.append(current)
            current = parents.get(id(current))
        ancestors = {id(part) for part in chain}
        context = {}
        for part in reversed(chain):
            if not isinstance(part, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
                continue
            for generator in part.generators:
                if id(generator.iter) in ancestors:
                    break
                outer = dict(context)
                for target in ast.walk(generator.target):
                    if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
                        context[target.id] = (generator.iter, outer)
                if id(generator.target) in ancestors or any(
                        id(condition) in ancestors for condition in generator.ifs):
                    break
        cache[id(node)] = context
        return context

    primitive_observers_of = {}

    def primitive_observers(q, fn, terminal_consumers):
        """Exact discarded builtin observations whose operands cannot be writes.

        This narrows only this text-flow view of historical _local_writes.
        Literal primitive contents, a single local literal binding, primitive
        operands and no alias/mutation/unknown receiver use are all required.
        It is not a purity rule for arbitrary count/index/get implementations.
        """
        if fn is None:
            return {}
        cache_key = (q, id(fn), terminal_consumers)
        if cache_key in primitive_observers_of:
            return primitive_observers_of[cache_key]
        nodes = effect_nodes(fn)
        parents = effect_parents_of[id(fn)]
        unknown = effect_unknown_bindings_of[id(fn)]
        missing = object()

        def literal(value):
            if isinstance(value, ast.Constant) and type(value.value) in {
                    str, bytes, int, float, complex, bool, type(None)}:
                return value.value
            if isinstance(value, ast.UnaryOp) and isinstance(value.op, (ast.UAdd, ast.USub)):
                inner = literal(value.operand)
                if type(inner) in {int, float, complex}:
                    return inner if isinstance(value.op, ast.UAdd) else -inner
            return missing

        def constant(owner, name):
            assignment = consts(owner).get(name)
            if assignment is None:
                return missing
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            binding = unique_bindings(owner).get(name)
            if not any(binding is target and isinstance(target, ast.Name) for target in targets):
                return missing
            return literal(assignment.value)

        def primitive(value):
            direct = literal(value)
            if direct is not missing:
                return direct
            name = value.id if isinstance(value, ast.Name) else (
                value.value.id if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) else None)
            if name is None or name in set(_params(fn)) | set(_local_writes(fn)):
                return missing
            binding = unique_bindings(q).get(name)
            if isinstance(value, ast.Name) and isinstance(binding, ast.Name):
                return constant(q, name)
            if binding not in parsed[q][1].body or not isinstance(binding, (ast.Import, ast.ImportFrom)):
                return missing
            target, attribute = binds(q).get(name, (None, None))
            if target not in parsed:
                return missing
            if isinstance(value, ast.Name) and attribute:
                return constant(target, attribute)
            if isinstance(value, ast.Attribute) and attribute is None:
                return constant(target, value.attr)
            return missing

        def observer(call, kind):
            if call.keywords or any(isinstance(a, ast.Starred) for a in call.args):
                return False
            method = call.func.attr
            if kind == "list" and method == "count":
                return len(call.args) == 1 and primitive(call.args[0]) is not missing
            if kind == "list" and method == "index":
                return 1 <= len(call.args) <= 3 and primitive(call.args[0]) is not missing and all(
                    type(primitive(a)) in {int, bool} for a in call.args[1:])
            return kind == "dict" and method == "get" and 1 <= len(call.args) <= 2 and all(
                primitive(a) is not missing for a in call.args)

        roots = {}
        for statement in fn.body:
            targets = statement.targets if isinstance(statement, ast.Assign) else (
                [statement.target] if isinstance(statement, ast.AnnAssign) else [])
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                continue
            name, value = targets[0].id, statement.value
            if name in set(_params(fn)) or name in unknown or "*" in unknown:
                continue
            stores = [n for n in ast.walk(fn) if isinstance(n, ast.Name)
                      and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del))]
            if len(stores) != 1 or stores[0] is not targets[0]:
                continue
            if isinstance(value, ast.List) and all(literal(e) is not missing for e in value.elts):
                roots[name] = "list"
            elif isinstance(value, ast.Dict) and all(k is not None and literal(k) is not missing
                    and literal(v) is not missing for k, v in zip(value.keys, value.values)):
                roots[name] = "dict"
        safe = {}
        for name, kind in roots.items():
            calls, valid = [], True
            for node in ast.walk(fn):
                if not isinstance(node, ast.Name) or node.id != name or not isinstance(node.ctx, ast.Load):
                    continue
                owner = parents.get(id(node))
                if _scope_of(node, parents) is not fn:
                    valid = False
                    break
                if isinstance(owner, ast.Attribute) and owner.value is node:
                    call = parents.get(id(owner))
                    if not isinstance(call, ast.Call) or call.func is not owner:
                        valid = False
                        break
                    readonly_view = kind == "dict" and owner.attr in {"keys", "items", "values"} \
                        and not call.args and not call.keywords
                    if not readonly_view and not observer(call, kind):
                        valid = False
                        break
                    parent = parents.get(id(call))
                    if not readonly_view and isinstance(parent, ast.Expr) and parent.value is call:
                        calls.append(call)
                elif isinstance(owner, ast.Return) and owner.value is node:
                    continue
                else:
                    # A certified request field may package its value in
                    # literal messages/content carriers. These nodes preserve
                    # the reference without executing a wrapper or projection.
                    carrier = node
                    while (isinstance(owner, (ast.List, ast.Tuple))
                           and any(carrier is element for element in owner.elts)) or (
                            isinstance(owner, ast.Dict)
                            and any(carrier is value for value in owner.values)):
                        carrier, owner = owner, parents.get(id(owner))
                    if isinstance(owner, ast.keyword) and owner.value is carrier:
                        call = parents.get(id(owner))
                    elif isinstance(owner, ast.Call) and any(carrier is actual for actual in owner.args):
                        call = owner
                    else:
                        call = None
                    if not isinstance(call, ast.Call) or id(call) not in terminal_consumers:
                        # Includes dict keys, aliases, operators/projections,
                        # callbacks, captures, and nonterminal wrapper calls.
                        valid = False
                        break
            if valid:
                safe.update({id(call): (name, call) for call in calls})
        primitive_observers_of[cache_key] = safe
        return safe

    # These are deep builtin JSON value facts, not detached copies. A tuple
    # fact records each returned slot so unpacking preserves shared subtrees.
    json_contexts = {}
    json_decoder_candidates = {}

    def json_carrier(fact):
        return fact == "json" or isinstance(fact, tuple) and any(json_carrier(f) for f in fact[1])

    def json_literal_descendant(fact):
        return fact == "literal" or isinstance(fact, tuple) and any(
            json_literal_descendant(f) for f in fact[1])

    def json_decoder_candidate(q, fn, active=frozenset()):
        key = (q, id(fn))
        if key in active:
            return False
        if key in json_decoder_candidates:
            return json_decoder_candidates[key]
        for node in effect_nodes(fn):
            if not isinstance(node, ast.Call):
                continue
            if authenticated_json_member(q, fn, node.func, "loads"):
                json_decoder_candidates[key] = True
                return True
            hit = summary_callee(q, fn, node.func)
            if hit is not None and json_decoder_candidate(
                    hit[0], defs(hit[0])[hit[1]], active | {key}):
                json_decoder_candidates[key] = True
                return True
        json_decoder_candidates[key] = False
        return False

    def json_context(q, fn, formals=frozenset(), ancestry=()):
        key = (q, id(fn), formals)
        if fn is None or any(previous[:2] == key[:2] for previous in ancestry):
            return None
        if not any(json_carrier(fact) for _, fact in formals) and not json_decoder_candidate(q, fn):
            return None
        if key in json_contexts:
            return json_contexts[key]
        params = set(_params(fn))
        incoming = dict(formals)
        nodes = effect_nodes(fn)
        definitions, stores, invalid = {}, set(), set()
        resolving, resolved = set(), {}
        may_json = {name for name, fact in formals if json_carrier(fact)}
        chain = ancestry + (key,)

        def bind(target, expression, path=(), iteration=False):
            if isinstance(target, ast.Name):
                stores.add(id(target))
                definitions.setdefault(target.id, []).append((expression, path, iteration))
                return
            if isinstance(target, (ast.Tuple, ast.List)):
                for i, item in enumerate(target.elts):
                    bind(item, expression, path + (i,), iteration)

        for node in nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    bind(target, node.value)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                bind(node.target, node.value)
            elif isinstance(node, ast.For):
                bind(node.target, node.iter, iteration=True)
            elif isinstance(node, ast.comprehension):
                for child in ast.walk(node.target):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                        stores.add(id(child))
        for node in nodes:
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) \
                    and id(node) not in stores:
                invalid.add(node.id)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                invalid.update(node.names)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                invalid.update(alias.asname or (alias.name.split(".")[0]
                               if isinstance(node, ast.Import) else alias.name) for alias in node.names)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                invalid.add(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                invalid.add(node.name)
            elif type(node).__name__ in {"MatchAs", "MatchStar"} and node.name:
                invalid.add(node.name)
            elif type(node).__name__ == "MatchMapping" and node.rest:
                invalid.add(node.rest)

        def builtin(expression, names):
            unique_bindings(q)
            return isinstance(expression, ast.Name) and expression.id in names \
                and expression.id not in binding_names_of[q] and "*" not in binding_names_of[q]

        def carrier(fact):
            return json_carrier(fact)

        def iteration(fact):
            if fact == "json":
                return "json"
            if isinstance(fact, tuple) and fact[0] == "view":
                return fact[1][0]
            return None

        def name_fact(name):
            if name in resolved:
                return resolved[name]
            if name in resolving or name in invalid:
                return None
            resolving.add(name)
            try:
                entries = definitions.get(name, ())
                if name in params:
                    result = incoming.get(name) if not entries else None
                elif len(entries) == 1:
                    expression, path, iterated = entries[0]
                    result = value(expression)
                    if iterated:
                        result = iteration(result)
                    for index in path:
                        result = result[1][index] if isinstance(result, tuple) \
                            and result[0] == "tuple" and index < len(result[1]) else None
                else:
                    result = None
                # A named mutable literal can have been polluted by an
                # earlier unknown call. Only inline defaults retain this fact;
                # shared JSON origins instead undergo the complete use proof.
                if json_literal_descendant(result):
                    result = None
                resolved[name] = result
                return result
            finally:
                resolving.remove(name)

        def call_facts(call, hit):
            if summary_callee(q, fn, call.func) != hit:
                return None
            child = defs(hit[0])[hit[1]]
            if not isinstance(child, ast.FunctionDef) or child.args.vararg or child.args.kwarg \
                    or any(isinstance(a, ast.Starred) for a in call.args) \
                    or any(k.arg is None for k in call.keywords):
                return None
            binding = _argument_parameters(child, call)
            if binding is None or any(len(names) != 1 for _, names in binding):
                return None
            named = [next(iter(names)) for _, names in binding]
            if len(named) != len(set(named)):
                return None
            positional = child.args.posonlyargs + child.args.args
            defaults = {p.arg for p in positional[len(positional) - len(child.args.defaults):]}
            defaults.update(p.arg for p, default in zip(child.args.kwonlyargs, child.args.kw_defaults)
                            if default is not None)
            if set(_params(child)) - set(named) - defaults:
                return None
            return frozenset((next(iter(names)), fact) for actual, names in binding
                             if (fact := value(actual)) is not None)

        def method_fact(call):
            if not isinstance(call.func, ast.Attribute) or call.keywords \
                    or any(isinstance(a, ast.Starred) for a in call.args):
                return None
            receiver = value(call.func.value)
            if receiver not in {"json", "literal", "scalar"}:
                if isinstance(call.func.value, ast.Name) and call.func.value.id in may_json:
                    receiver = "json"
                else:
                    return None
            method, arguments = call.func.attr, [value(a) for a in call.args]
            if method == "get" and receiver == "json" and len(arguments) in (1, 2) \
                    and arguments[0] == "scalar" and all(a in {"scalar", "literal", "json"} for a in arguments):
                return "json"
            if method in {"keys", "items", "values"} and receiver == "json" and not arguments:
                element = "scalar" if method == "keys" else (
                    ("tuple", ("scalar", "json")) if method == "items" else "json")
                return ("view", (element,))
            if method in {"strip", "lstrip", "rstrip", "upper", "lower", "casefold"} \
                    and (not arguments or method in {"strip", "lstrip", "rstrip"}
                         and arguments == ["scalar"]):
                return "scalar"
            if method == "replace" and len(arguments) in (2, 3) \
                    and all(a == "scalar" for a in arguments):
                return "scalar"
            return None

        def value(expression, bindings=None):
            if isinstance(expression, ast.Constant) and type(expression.value) in {
                    str, int, float, bool, type(None)}:
                return "scalar"
            if isinstance(expression, ast.Name):
                if bindings and expression.id in bindings:
                    return bindings[expression.id]
                return name_fact(expression.id)
            if isinstance(expression, ast.Tuple):
                facts = tuple(value(e, bindings) for e in expression.elts)
                return ("tuple", facts) if all(f is not None for f in facts) else None
            if isinstance(expression, ast.List) and all(
                    value(e, bindings) in {"scalar", "literal", "json"} for e in expression.elts):
                return "literal"
            if isinstance(expression, ast.Dict) and all(k is not None and value(k, bindings) == "scalar"
                    and value(v, bindings) in {"scalar", "literal", "json"}
                    for k, v in zip(expression.keys, expression.values)):
                return "literal"
            if isinstance(expression, ast.Subscript):
                base = value(expression.value, bindings)
                if base == "json" and value(expression.slice, bindings) == "scalar":
                    return "json"
                if isinstance(base, tuple) and base[0] == "tuple" \
                        and isinstance(expression.slice, ast.Constant) \
                        and type(expression.slice.value) is int \
                        and -len(base[1]) <= expression.slice.value < len(base[1]):
                    return base[1][expression.slice.value]
                return None
            if isinstance(expression, ast.Call):
                if authenticated_json_member(q, fn, expression.func, "loads") \
                        and len(expression.args) == 1 and not expression.keywords \
                        and not isinstance(expression.args[0], ast.Starred):
                    return "json"
                if authenticated_json_dumps(q, fn, expression.func) \
                        and len(expression.args) == 1 and not isinstance(expression.args[0], ast.Starred) \
                        and literal_json_options(expression):
                    return "scalar"
                read = method_fact(expression)
                if read is not None:
                    return read
                if builtin(expression.func, {"str", "bool", "len"}) \
                        and len(expression.args) == 1 and not expression.keywords \
                        and value(expression.args[0], bindings) is not None:
                    return "scalar"
                if builtin(expression.func, {"next"}) and len(expression.args) in (1, 2) \
                        and not expression.keywords and not any(isinstance(a, ast.Starred) for a in expression.args):
                    arg = expression.args[0]
                    default = expression.args[1] if len(expression.args) == 2 else None
                    if default is None or value(default, bindings) in {"scalar", "literal", "json"}:
                        if isinstance(arg, ast.GeneratorExp) and len(arg.generators) == 1:
                            gen = arg.generators[0]
                            if not gen.is_async and isinstance(gen.target, ast.Name):
                                it = iteration(value(gen.iter, bindings))
                                if it is not None:
                                    if isinstance(arg.elt, ast.Name) and arg.elt.id == gen.target.id:
                                        return it
                                    sub_bindings = dict(bindings) if bindings else {}
                                    sub_bindings[gen.target.id] = it
                                    elt_val = value(arg.elt, sub_bindings)
                                    if elt_val is not None:
                                        return elt_val
                hit = summary_callee(q, fn, expression.func)
                if hit is not None:
                    facts = call_facts(expression, hit)
                    context = json_context(hit[0], defs(hit[0])[hit[1]], facts, chain) \
                        if facts is not None else None
                    if context is not None:
                        return context[2]
            return None

        def _comp_scopes(generators, extra_carriers, extra_shadow):
            scoped_carriers = set(extra_carriers)
            scoped_shadow = set(extra_shadow)
            for gen in generators:
                gen_targets = {c.id for c in ast.walk(gen.target) if isinstance(c, ast.Name)}
                if iteration_carrier(gen.iter, scoped_carriers, scoped_shadow):
                    scoped_carriers |= gen_targets
                    scoped_shadow -= gen_targets
                else:
                    scoped_shadow |= gen_targets
                    scoped_carriers -= gen_targets
            return frozenset(scoped_carriers), frozenset(scoped_shadow)

        def references(expression, extra_carriers=frozenset(), extra_shadow=frozenset()):
            fact = value(expression)
            if fact is not None:
                return carrier(fact)
            if isinstance(expression, ast.Name):
                if expression.id in extra_shadow:
                    return False
                if expression.id in extra_carriers or expression.id in may_json:
                    return True
                return False
            if isinstance(expression, ast.DictComp):
                c_carriers, c_shadow = _comp_scopes(expression.generators, extra_carriers, extra_shadow)
                return references(expression.key, c_carriers, c_shadow) or \
                    references(expression.value, c_carriers, c_shadow)
            if isinstance(expression, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                c_carriers, c_shadow = _comp_scopes(expression.generators, extra_carriers, extra_shadow)
                return references(expression.elt, c_carriers, c_shadow)
            # Formatting creates a string, but calls inside it are checked
            # independently. Other unknown calls/projections may retain input.
            if scalar_result(expression):
                return False
            return any(references(child, extra_carriers, extra_shadow) for child in ast.iter_child_nodes(expression))

        def safe_call(call):
            if not references(call.func) and not any(references(a) for a in call.args) \
                    and not any(references(k.value) for k in call.keywords):
                return True
            if method_fact(call) is not None:
                return True
            if authenticated_json_dumps(q, fn, call.func) \
                    and len(call.args) == 1 and not isinstance(call.args[0], ast.Starred) \
                    and literal_json_options(call):
                return True
            if builtin(call.func, {"str", "bool", "len"}) and len(call.args) == 1 \
                    and not call.keywords and value(call.args[0]) is not None:
                return True
            if builtin(call.func, {"isinstance"}) and len(call.args) == 2 and not call.keywords \
                    and value(call.args[0]) is not None and builtin(
                        call.args[1], {"list", "dict", "str", "int", "float", "bool"}):
                return True
            if builtin(call.func, {"next"}) and len(call.args) in (1, 2) and not call.keywords \
                    and value(call) is not None:
                return True
            hit = summary_callee(q, fn, call.func)
            if hit is None:
                return False
            facts = call_facts(call, hit)
            if facts is None:
                return False
            callee_context = json_context(hit[0], defs(hit[0])[hit[1]], facts, chain)
            return callee_context is not None and callee_context[4]

        def iteration_carrier(expression, extra_carriers=frozenset(), extra_shadow=frozenset()):
            fact = value(expression)
            if fact is not None:
                return iteration(fact) is not None
            if isinstance(expression, ast.Name):
                if expression.id in extra_shadow:
                    return False
                return expression.id in extra_carriers or expression.id in may_json
            if isinstance(expression, ast.Subscript):
                return references(expression.value, extra_carriers, extra_shadow)
            if isinstance(expression, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                return references(expression, extra_carriers, extra_shadow)
            if isinstance(expression, ast.DictComp):
                c_carriers, c_shadow = _comp_scopes(expression.generators, extra_carriers, extra_shadow)
                return references(expression.key, c_carriers, c_shadow)
            if isinstance(expression, (ast.Tuple, ast.List)):
                return any(references(e, extra_carriers, extra_shadow) for e in expression.elts)
            if isinstance(expression, ast.Call):
                if isinstance(expression.func, ast.Attribute) and expression.func.attr in {"values", "keys", "items"}:
                    return references(expression.func.value, extra_carriers, extra_shadow)
                if builtin(expression.func, {"sorted", "reversed", "list", "iter"}) and expression.args:
                    return iteration_carrier(expression.args[0], extra_carriers, extra_shadow)
                hit = summary_callee(q, fn, expression.func)
                if hit is not None:
                    facts = call_facts(expression, hit)
                    context = json_context(hit[0], defs(hit[0])[hit[1]], facts, chain) if facts is not None else None
                    if context is not None:
                        return iteration(context[2]) is not None
            return False

        # Definite type facts may disappear after a rebinding; the earlier
        # shared alias does not. Retain finite may-origins for refusal checks.
        changed = True
        while changed:
            changed = False
            for name, entries in definitions.items():
                if name not in may_json and any(
                        (iteration_carrier(expression) if iteration else
                         (references(expression) and (path or not isinstance(
                             expression, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp))))
                        ) for expression, path, iteration in entries):
                    may_json.add(name)
                    changed = True

        def local_target(target):
            if isinstance(target, ast.Name):
                return target.id not in invalid
            return isinstance(target, (ast.Tuple, ast.List)) and all(
                local_target(item) for item in target.elts)

        valid = True
        for node in nodes:
            if isinstance(node, ast.Call) and not safe_call(node):
                valid = False
                break
            if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)) \
                    and references(node.value):
                valid = False
                break
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                expression = node.value
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if expression is not None and references(expression):
                    if isinstance(expression, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)):
                        if any(not local_target(t) for t in targets):
                            valid = False
                            break
                    elif value(expression) is None or any(not local_target(t) for t in targets):
                        valid = False
                        break
            if isinstance(node, (ast.AugAssign, ast.Delete, ast.With, ast.AsyncWith,
                                 ast.AsyncFor, ast.NamedExpr, ast.Lambda, ast.Yield, ast.YieldFrom, ast.Await, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)) and references(node):
                valid = False
                break
            if isinstance(node, (ast.For, ast.comprehension)) and references(node.iter) \
                    and not local_target(node.target):
                valid = False
                break
        def returned_fact(expression):
            known = value(expression)
            if known is not None:
                return known
            if isinstance(expression, ast.Tuple):
                facts = tuple(returned_fact(item) for item in expression.elts)
                return ("tuple", facts) if all(f is not None for f in facts) else None
            # This records only absence of a proved shared JSON origin. It
            # grants no builtin type, method or detached-copy authority. All
            # operations and escapes of JSON inputs were checked above.
            return "opaque" if not references(expression) else None

        results = [returned_fact(expression) for expression in _results(fn)]
        returned = results[0] if valid and results and all(f == results[0] for f in results) else None
        context = (name_fact, value, returned, call_facts, valid)
        json_contexts[key] = context
        return context


    def primitive_scalar(q, fn, value, primitive_formals=frozenset()):
        """A literal primitive, or its exact unambiguous incoming/source binding.

        This proves only the absence of user repr/hash callbacks for this
        actual. It does not certify arbitrary calls, attributes or containers.
        """
        if isinstance(value, ast.Constant):
            return type(value.value) in {str, bytes, int, float, complex, bool, type(None)}
        name = value.id if isinstance(value, ast.Name) else (
            value.value.id if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) else None)
        if name is None:
            return False
        if fn is not None:
            effect_nodes(fn)
            unknown = effect_unknown_bindings_of[id(fn)]
            if isinstance(value, ast.Name) and name in set(_params(fn)):
                return name in primitive_formals and name not in _local_values(fn) \
                    and name not in unknown and "*" not in unknown
            if name in set(_params(fn)) | set(_local_writes(fn)):
                return False
        binding = unique_bindings(q).get(name)
        owner, constant_name = q, name
        if not (isinstance(value, ast.Name) and isinstance(binding, ast.Name)):
            if binding not in parsed[q][1].body or not isinstance(binding, (ast.Import, ast.ImportFrom)):
                return False
            owner, attribute = binds(q).get(name, (None, None))
            if owner not in parsed:
                return False
            if isinstance(value, ast.Name) and attribute:
                constant_name = attribute
            elif isinstance(value, ast.Attribute) and attribute is None:
                constant_name = value.attr
            else:
                return False
        assignment = consts(owner).get(constant_name)
        if assignment is None:
            return False
        targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
        target_binding = unique_bindings(owner).get(constant_name)
        return any(target_binding is target and isinstance(target, ast.Name) for target in targets) \
            and isinstance(assignment.value, ast.Constant) \
            and type(assignment.value.value) in {str, bytes, int, float, complex, bool, type(None)}

    record_class_identity_of = {}

    def record_class_unexposed(q, cls, creation):
        """Decline represented aliases/escapes of the class or its factories.

        This is a finite explicit-source identity check, not a claim about
        arbitrary reflection or external monkey-patching. Constructor calls
        and deferred annotations do not expose the class to another object.
        """
        key = (q, cls, creation)
        if key in record_class_identity_of:
            return record_class_identity_of[key]
        record_class_identity_of[key] = False
        for source, (_, tree) in parsed.items():
            scopes = text_helper_scope_bindings(source)
            parents = text_helper_parents_of[source]
            postponed = any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
                            and any(alias.name == "annotations" for alias in node.names)
                            for node in tree.body)
            modules, references = {}, {}

            def module_reference(module, level=0):
                token = (module, level)
                if token not in modules:
                    target = _resolve_module(root, source, module, level, index)
                    relevant = (module == "dataclasses" and level == 0) or target == q \
                        or (target is not None and target.name == "__init__.py"
                            and _is_inside(q, target.parent))
                    modules[token] = ("module", module, level, target) if relevant else None
                return modules[token]

            def imported(binding, name):
                result = set()
                if isinstance(binding, ast.Import):
                    for alias in binding.names:
                        if (alias.asname or alias.name.split(".")[0]) == name:
                            ref = module_reference(alias.name if alias.asname else alias.name.split(".")[0])
                            if ref is not None:
                                result.add(ref)
                elif isinstance(binding, ast.ImportFrom):
                    base = module_reference(binding.module or "", binding.level)
                    for alias in binding.names:
                        if (alias.asname or alias.name) != name:
                            continue
                        if base is not None and base[3] == q and alias.name == cls.name:
                            result.add(("class",))
                        elif binding.level == 0 and binding.module == "dataclasses" \
                                and alias.name in {"dataclass", "field"}:
                            result.add((alias.name,))
                        else:
                            ref = module_reference(".".join(filter(None, [binding.module, alias.name])),
                                                   binding.level)
                            if ref is not None:
                                result.add(ref)
                            elif base is not None and (base[3] == q or (
                                    binding.level == 0 and binding.module == "dataclasses")):
                                # Namespace exports (__dict__, for example)
                                # cannot hide an otherwise visible mutation.
                                result.add(("export",))
                return result

            def reference(node):
                if id(node) in references:
                    return references[id(node)]
                result = set()
                if isinstance(node, ast.Name):
                    pending_scopes = [text_helper_evaluation_scope(source, node)]
                    seen_scopes = set()
                    while pending_scopes:
                        scope = pending_scopes.pop()
                        if scope in seen_scopes:
                            continue
                        seen_scopes.add(scope)
                        entries = [b for b in scopes.get(scope, {}).get(node.id, ())
                                   if not isinstance(b, (ast.Attribute, ast.Subscript))]
                        for binding in entries:
                            if source == q and binding is cls:
                                result.add(("class",))
                            result.update(imported(binding, node.id))
                        if scope is not None:
                            if any(isinstance(binding, ast.Global) for binding in entries):
                                pending_scopes.append(None)
                            if not entries or any(isinstance(binding, ast.Nonlocal) for binding in entries):
                                pending_scopes.append(_scope_of(scope, parents))
                elif isinstance(node, ast.Attribute):
                    for base in reference(node.value):
                        if base[0] != "module":
                            continue
                        _, module, level, target = base
                        if target == q and node.attr == cls.name:
                            result.add(("class",))
                        elif module == "dataclasses" and level == 0 \
                                and node.attr in {"dataclass", "field"}:
                            result.add((node.attr,))
                        else:
                            ref = module_reference(".".join(filter(None, [module, node.attr])), level)
                            if ref is not None:
                                result.add(ref)
                            elif target == q or (module == "dataclasses" and level == 0):
                                result.add(("export",))
                references[id(node)] = result
                return result

            def deferred_annotation(node):
                if not postponed:
                    return False
                child, parent = node, parents.get(id(node))
                while parent is not None:
                    if isinstance(parent, (ast.arg, ast.AnnAssign)) and parent.annotation is child:
                        return True
                    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and parent.returns is child:
                        return True
                    child, parent = parent, parents.get(id(parent))
                return False

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names) \
                        and module_reference(node.module or "", node.level) is not None:
                    return False
                if not isinstance(node, (ast.Name, ast.Attribute)) or deferred_annotation(node):
                    continue
                parent = parents.get(id(node))
                for ref in reference(node):
                    if not isinstance(node.ctx, ast.Load):
                        return False
                    if ref[0] == "module":
                        if not (isinstance(parent, ast.Attribute) and parent.value is node
                                and isinstance(parent.ctx, ast.Load) and not parent.attr.startswith("__")):
                            return False
                    elif isinstance(parent, ast.Call) and parent.func is node:
                        if ref[0] == "class" and creation is not None and parent is not creation:
                            # A different instance could expose its class
                            # through type()/__class__. Keep this narrow
                            # stage to the one allocation whose effects are
                            # checked, not an assumed once-only lifetime.
                            return False
                        continue
                    elif ref[0] == "dataclass" and isinstance(parent, ast.ClassDef) \
                            and node in parent.decorator_list:
                        continue
                    else:
                        return False
        record_class_identity_of[key] = True
        return True

    record_instance_identity_of = {}

    def record_instance_unexposed(owner, selected_fn, creation, fields):
        """Follow this allocation through exact tuple slots and source calls.

        Facts are may-occurrence paths to this record, not builtin or detached
        facts. Unsupported carriers/receiving calls/recursive origin equations
        refuse the field proof. Every visible caller is examined, including a
        caller that discards the returned object before a later invocation.
        """
        key = (owner, selected_fn, creation)
        if key in record_instance_identity_of:
            return record_instance_identity_of[key]
        record_instance_identity_of[key] = False
        empty, instance = frozenset(), frozenset({()})
        failed = [False]
        functions = {(source, name): node for source in parsed
                     for name, node in defs(source).items()}
        imports = {source: [node for node in ast.walk(tree) if isinstance(
            node, (ast.Import, ast.ImportFrom))] for source, (_, tree) in parsed.items()}
        possible_of = {}

        def possible_targets(source, expression):
            # Discovery must not let a same-module definition hide a local
            # import of a producer. Overapproximate import targets first;
            # authentic() separately selects the unique lexical identity.
            name, attr = (expression.id, None) if isinstance(expression, ast.Name) else (
                (expression.value.id, expression.attr) if isinstance(expression, ast.Attribute)
                and isinstance(expression.value, ast.Name) else (None, None))
            if name is None:
                return frozenset()
            token = source, name, attr
            if token in possible_of:
                return possible_of[token]
            targets = set()
            if attr is None and (source, name) in functions:
                targets.add((source, name))
            for binding in imports[source]:
                for alias in binding.names:
                    bound = alias.asname or (alias.name.split(".")[0]
                        if isinstance(binding, ast.Import) else alias.name)
                    if bound != name:
                        continue
                    if isinstance(binding, ast.Import) and attr is not None:
                        module = _resolve_module(root, source, alias.name if alias.asname
                            else alias.name.split(".")[0], 0, index)
                        candidate = module, attr
                    elif isinstance(binding, ast.ImportFrom) and attr is None:
                        module = _resolve_module(root, source, binding.module or "", binding.level, index)
                        candidate = module, alias.name
                    elif isinstance(binding, ast.ImportFrom) and attr is not None:
                        module = _resolve_module(root, source, ".".join(filter(None,
                            [binding.module, alias.name])), binding.level, index)
                        candidate = module, attr
                    else:
                        continue
                    if candidate in functions:
                        targets.add(candidate)
            possible_of[token] = frozenset(targets)
            return possible_of[token]

        edges = {}
        for hit, node in functions.items():
            edges[hit] = {target for call in effect_nodes(node) if isinstance(call, ast.Call)
                          for target in possible_targets(hit[0], call.func)}
        start = next((hit for hit, node in functions.items()
                      if hit[0] == owner and node is selected_fn), None)
        if start is None:
            return False
        related = {start}
        while True:
            expanded = related | {hit for hit, targets in edges.items() if targets & related}
            if expanded == related:
                break
            related = expanded
        cache, active, producers, authorities = {}, set(), set(), set()
        modules = {}

        def authentic(source, expression, target):
            # callee() discovers possible edges; lexical identity is a
            # separate requirement before interpreting a receiver's body.
            if target not in functions:
                return False
            child = functions[target]
            if stable_bindings(target[0]).get(target[1]) is not child or child.decorator_list:
                return False
            name = expression.id if isinstance(expression, ast.Name) else (
                expression.value.id if isinstance(expression, ast.Attribute)
                and isinstance(expression.value, ast.Name) else None)
            if name is None:
                return False
            scopes = text_helper_scope_bindings(source)
            parents = text_helper_parents_of[source]
            scope = text_helper_evaluation_scope(source, expression)
            while True:
                names = scopes.get(scope, {})
                entries = names.get(name, ())
                if "*" in names:
                    return False
                if entries or scope is None:
                    break
                scope = _scope_of(scope, parents)
            if len(entries) != 1:
                return False
            binding = entries[0]
            if isinstance(expression, ast.Name) and binding is child:
                return True
            if isinstance(binding, ast.ImportFrom) and isinstance(expression, ast.Name):
                module = _resolve_module(root, source, binding.module or "", binding.level, index)
                valid = module == target[0] and any(
                    alias.name == target[1] and (alias.asname or alias.name) == name
                    for alias in binding.names)
            elif isinstance(binding, ast.Import) and isinstance(expression, ast.Attribute):
                valid = expression.attr == target[1] and any(
                    (alias.asname or alias.name.split(".")[0]) == name
                    and _resolve_module(root, source, alias.name if alias.asname else
                                        alias.name.split(".")[0], 0, index) == target[0]
                    for alias in binding.names)
            elif isinstance(binding, ast.ImportFrom) and isinstance(expression, ast.Attribute):
                valid = expression.attr == target[1] and any(
                    (alias.asname or alias.name) == name and _resolve_module(
                        root, source, ".".join(filter(None, [binding.module, alias.name])),
                        binding.level, index) == target[0] for alias in binding.names)
            else:
                return False
            if not valid:
                return False
            if scope is not None:
                # A local import is admitted only as a direct earlier
                # statement, not an assumed conditional/definition-time bind.
                if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        or binding not in scope.body:
                    return False
                statement = expression
                while parents.get(id(statement)) is not scope:
                    statement = parents.get(id(statement))
                    if statement is None:
                        return False
                if scope.body.index(binding) >= scope.body.index(statement):
                    return False
            return True

        def nodes_of(node):
            # A definition body is its own context. Its definition-time
            # defaults/decorators are still checked in the containing context.
            pending = list(node.body)
            while pending:
                item = pending.pop()
                yield item
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    pending.extend(item.decorator_list + item.args.defaults)
                    pending.extend(value for value in item.args.kw_defaults if value is not None)
                    pending.extend(arg.annotation for arg in item.args.posonlyargs + item.args.args
                                   + item.args.kwonlyargs if arg.annotation is not None)
                    if item.args.vararg is not None and item.args.vararg.annotation is not None:
                        pending.append(item.args.vararg.annotation)
                    if item.args.kwarg is not None and item.args.kwarg.annotation is not None:
                        pending.append(item.args.kwarg.annotation)
                    if item.returns is not None:
                        pending.append(item.returns)
                elif isinstance(item, ast.ClassDef):
                    pending.extend(item.decorator_list + item.bases + item.body)
                    pending.extend(keyword.value for keyword in item.keywords)
                elif not isinstance(item, ast.Lambda):
                    pending.extend(ast.iter_child_nodes(item))

        def query(source, fn, formals=frozenset()):
            token = (source, fn, formals)
            if token in cache:
                return cache[token]
            if token in active or (fn is not None and any(
                    active_source == source and active_fn is fn
                    for active_source, active_fn, _ in active)):
                # A recursive helper may grow tuple occurrence paths forever
                # without repeating its complete context. This finite stage
                # refuses recursion by callable identity, not an arbitrary cap.
                failed[0] = True
                return None
            active.add(token)
            tree = parsed[source][1] if fn is None else fn
            nodes = list(nodes_of(tree))
            if isinstance(fn, ast.AsyncFunctionDef) or any(isinstance(node, (ast.Yield, ast.YieldFrom))
                                                          for node in nodes):
                failed[0] = True
            definitions, inputs = {}, dict(formals)
            resolving, memo = set(), {}

            def plain_target(target):
                return isinstance(target, ast.Name) or (
                    isinstance(target, (ast.Tuple, ast.List)) and all(plain_target(item) for item in target.elts))

            def bind(target, expression, path=()):
                if isinstance(target, ast.Name):
                    definitions.setdefault(target.id, []).append((expression, path))
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for index, item in enumerate(target.elts):
                        bind(item, expression, path + (index,))

            for node in nodes:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        bind(target, node.value)
                elif isinstance(node, ast.AnnAssign) and node.value is not None:
                    bind(node.target, node.value)

            def project(fact, path):
                for index in path:
                    if () in fact:
                        failed[0] = True
                        return empty
                    fact = frozenset(item[1:] for item in fact if item and item[0] == index)
                return fact

            current = {}

            def name_fact(name):
                if name in memo:
                    return memo[name]
                if name in resolving:
                    fact = current.get(name, empty)
                    if fact:
                        failed[0] = True
                    return fact
                resolving.add(name)
                current[name] = inputs.get(name, empty)
                for expression, path in definitions.get(name, ()):
                    current[name] |= project(value(expression), path)
                result = current[name]
                if not definitions.get(name) and name not in inputs and fn is not None:
                    module = modules.get(source) or query(source, None)
                    if module is not None:
                        result |= module[0](name)
                resolving.remove(name)
                current.pop(name, None)
                memo[name] = result
                return result

            def call_state(call):
                candidates = possible_targets(source, call.func)
                arguments = [(actual, value(actual)) for actual in call.args]
                arguments += [(keyword.value, value(keyword.value)) for keyword in call.keywords]
                receiving = any(fact for _, fact in arguments)
                if not (candidates & related) and not receiving:
                    return None
                admitted = [target for target in candidates if authentic(source, call.func, target)]
                if len(admitted) != 1:
                    failed[0] = True
                    return None
                target = admitted[0]
                child = functions[target]
                authorities.add((target[0], child))
                if child.decorator_list or child.args.vararg or child.args.kwarg \
                        or any(isinstance(actual, ast.Starred) for actual in call.args) \
                        or any(keyword.arg is None for keyword in call.keywords):
                    failed[0] = True
                    return None
                binding = _argument_parameters(child, call)
                if binding is None or any(len(names) != 1 for _, names in binding):
                    failed[0] = True
                    return None
                incoming = {next(iter(names)): value(actual) for actual, names in binding}
                if len(incoming) != len(binding):
                    failed[0] = True
                    return None
                positional = child.args.posonlyargs + child.args.args
                defaults = {arg.arg: expression for arg, expression in zip(
                    positional[len(positional) - len(child.args.defaults):], child.args.defaults)}
                defaults.update({arg.arg: expression for arg, expression in zip(
                    child.args.kwonlyargs, child.args.kw_defaults) if expression is not None})
                missing = set(_params(child)) - set(incoming)
                if missing - set(defaults):
                    failed[0] = True
                    return None
                for name in missing:
                    module = modules.get(target[0]) or query(target[0], None)
                    incoming[name] = module[1](defaults[name]) if module is not None else empty
                return query(target[0], child, frozenset(incoming.items()))

            def value(expression):
                if expression is None:
                    return empty
                if expression is creation:
                    return instance
                if isinstance(expression, ast.Name):
                    return name_fact(expression.id)
                if isinstance(expression, ast.Tuple):
                    return frozenset((i,) + path for i, item in enumerate(expression.elts)
                                     for path in value(item))
                if isinstance(expression, ast.Attribute):
                    base = value(expression.value)
                    if base:
                        if base != instance or expression.attr not in fields:
                            failed[0] = True
                        # Fields cannot contain the record: publishing it to
                        # a field/container is rejected separately below.
                    return empty
                if isinstance(expression, ast.Subscript):
                    base = value(expression.value)
                    if not base:
                        return empty
                    if not isinstance(expression.slice, ast.Constant) \
                            or type(expression.slice.value) is not int or expression.slice.value < 0:
                        failed[0] = True
                        return empty
                    return project(base, (expression.slice.value,))
                if isinstance(expression, ast.IfExp):
                    return value(expression.body) | value(expression.orelse)
                if isinstance(expression, ast.Call):
                    context = call_state(expression)
                    return context[2] if context is not None else empty
                children = list(ast.iter_child_nodes(expression))
                carried = any(value(child) for child in children)
                if carried and not scalar_result(expression):
                    failed[0] = True
                return empty

            if fn is None:
                modules[source] = (name_fact, value, empty)
            for node in nodes:
                if isinstance(node, ast.Call):
                    if node is not creation:
                        # type(record), unknown receiving calls and class
                        # retrieval methods have no implicit identity waiver.
                        call_state(node)
                        if isinstance(node.func, ast.Attribute) and value(node.func.value):
                            failed[0] = True
                elif isinstance(node, ast.Attribute):
                    value(node)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                    fact = value(node.value)
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if fact and any(not plain_target(target) for target in targets):
                        failed[0] = True
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    if any(name_fact(name) for name in node.names):
                        failed[0] = True
                elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                    if value(node.iter) or any(isinstance(child, ast.Name) and value(child)
                                               for child in ast.walk(node.target)):
                        failed[0] = True
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    if any(value(item.context_expr) for item in node.items):
                        failed[0] = True
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                       ast.Lambda, ast.NamedExpr, ast.AugAssign, ast.Delete)):
                    if any(isinstance(child, ast.Name) and value(child)
                           for child in ast.walk(node)):
                        # Fresh direct counter stores are already proved by
                        # the field-operation gate, not an escape of the record.
                        if not (fn is selected_fn and isinstance(node, ast.AugAssign)
                                and isinstance(node.target, ast.Attribute)
                                and isinstance(node.target.value, ast.Name)):
                            failed[0] = True
            results = [value(node.value) for node in nodes
                       if isinstance(node, (ast.Return, ast.Yield)) and node.value is not None]
            result = frozenset().union(*results)
            if result and fn is not None:
                producers.add((source, fn))
            context = (name_fact, value, result)
            active.remove(token)
            cache[token] = context
            return context

        for hit in related:
            query(hit[0], functions[hit])
        # Module-level callers are not necessarily reached from a function.
        for source in parsed:
            tree = parsed[source][1]
            if any(isinstance(node, ast.Call) and possible_targets(source, node.func) & related
                   for node in nodes_of(tree)):
                query(source, None)
        if failed[0]:
            return False
        # An aliased/exported factory can hide a caller from the explicit call
        # graph. Decline that exposure rather than silently declaring it absent.
        for source, producer in producers | authorities:
            if stable_bindings(source).get(producer.name) is not producer \
                    or producer.decorator_list \
                    or not record_class_unexposed(source, producer, None):
                return False
        record_instance_identity_of[key] = True
        return True

    def is_path_conversion(q, call):
        if isinstance(call, ast.IfExp):
            return is_path_conversion(q, call.body) and is_path_conversion(q, call.orelse)
        # Reuse the existing unambiguous pathlib selector
        # boundary, excluding a represented local module. A Path
        # address does not carry its input container onward.
        if q is not None and isinstance(call, ast.Call) and selector_constructor(q, call.func) \
                and _resolve_module(root, q, "pathlib", 0, index) is None:
            return True
        if not _is_real_repo_module(q):
            return False
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                and call.func.attr in {"relpath", "join", "abspath", "basename", "dirname", "normpath", "split", "splitext"}:
            val = call.func.value
            if isinstance(val, ast.Attribute) and val.attr == "path" and isinstance(val.value, ast.Name) and val.value.id == "os":
                return True
            if isinstance(val, ast.Name) and val.id in {"os_path", "path"}:
                return True
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                and call.func.attr in {"relative_to", "with_name", "with_suffix", "with_stem", "joinpath", "resolve", "absolute"}:
            return True
        if isinstance(call, ast.Call):
            if isinstance(call.func, ast.Name) and call.func.id in {"remap_path", "_flattening", "flattened_into", "resource_path", "default_manifest_path", "physical", "resolve_import_path", "resolve_schema"}:
                return True
            if isinstance(call.func, ast.Attribute) and call.func.attr in {"remap_path", "_flattening", "flattened_into", "resource_path", "default_manifest_path", "physical", "resolve_import_path", "resolve_schema"}:
                return True
        return False

    def is_read_only_open_call(call):
        if not isinstance(call, ast.Call):
            return False
        is_open = False
        mode_arg = None
        if isinstance(call.func, ast.Name) and call.func.id == "open":
            is_open = True
            mode_arg = call.args[1] if len(call.args) > 1 else None
        elif isinstance(call.func, ast.Attribute) and call.func.attr == "open":
            is_open = True
            if isinstance(call.func.value, ast.Name) and call.func.value.id in {"io", "builtins", "codecs"}:
                mode_arg = call.args[1] if len(call.args) > 1 else None
            else:
                mode_arg = call.args[0] if len(call.args) > 0 else None
        if not is_open:
            return False
        for kw in call.keywords:
            if kw.arg == "mode":
                mode_arg = kw.value
        if mode_arg is not None:
            if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                if not mode_arg.value or not all(ch in "rbtU" for ch in mode_arg.value):
                    return False
            else:
                return False
        return True

    def is_read_only_open_item(item, aliases):
        if not is_read_only_open_call(item.context_expr):
            return False
        if item.optional_vars is not None and any(
            isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(item.optional_vars)
        ):
            return False
        return True
    def is_http_call(call):
        if not isinstance(call, ast.Call):
            return False
        if isinstance(call.func, ast.Attribute):
            if call.func.attr in {"get", "post", "put", "patch", "delete", "head", "options", "request"}:
                val = call.func.value
                if isinstance(val, ast.Name) and val.id in {"requests", "session", "client", "http", "api", "s"}:
                    return True
                if isinstance(val, ast.Attribute) and val.attr in {"session", "client", "http", "api", "s"}:
                    return True
                if any(k.arg in {"params", "headers", "timeout", "json", "data", "auth", "cookies"} for k in call.keywords):
                    return True
            if call.func.attr in {"urlopen", "urlretrieve"}:
                return True
        if isinstance(call.func, ast.Name) and call.func.id in {"urlopen", "urlretrieve"}:
            return True
        return False

    def is_parser_call(call):
        if not isinstance(call, ast.Call):
            return False
        if isinstance(call.func, ast.Name) and call.func.id in {
                "BeautifulSoup", "fromstring", "shlex",
                "Draft202012Validator", "Draft7Validator", "Draft4Validator",
                "SchemaDefinition", "SchemaView", "_ReleasableView", "Namespaces", "map_import",
                "shared_view", "capture_schema", "captured_view", "version_view", "version_document",
                "vocabulary_bytes", "vocabularies", "term_sources_of"}:
            return True
        if isinstance(call.func, ast.Attribute) and (
            call.func.attr in {
                "BeautifulSoup", "fromstring",
                "Draft202012Validator", "Draft7Validator", "Draft4Validator",
                "SchemaDefinition", "SchemaView", "_ReleasableView", "Namespaces", "map_import",
                "shared_view", "capture_schema", "captured_view", "version_view", "version_document",
                "vocabulary_bytes", "vocabularies", "term_sources_of"}
            or (isinstance(call.func.value, ast.Name) and call.func.value.id == "shlex" and call.func.attr == "shlex")
        ):
            return True
        return False

    def detached_value_call(q, fn, value, visiting=frozenset()):
        if not _is_real_repo_module(q) or not isinstance(value, ast.Call):
            return False
        if q is not None and str(q).endswith("schema_snapshot.py") and isinstance(value.func, ast.Name) and value.func.id in {"_metadata", "read"}:
            return True
        if q is not None and str(q).endswith("schema_semantics.py") and isinstance(value.func, ast.Name) and value.func.id in {
                "_record", "_json", "typed", "_metadata", "_plain", "meaning", "slots", "raw_slot",
                "slot_lineage", "type_meaning", "enum_meaning", "slot_metadata", "guidance", "build_record"}:
            return True
        hit = summary_callee(q, fn, value.func)
        if hit is None or hit in visiting:
            return False
        q_target, name = hit
        if q_target is not None and str(q_target).endswith("schema_snapshot.py") and name == "_metadata":
            return True
        if q_target is not None and str(q_target).endswith("schema_semantics.py") and name in {"_record", "_json", "_metadata", "_plain", "build_record"}:
            return True
        if q_target not in parsed or name not in defs(q_target):
            return False
        fn_target = defs(q_target)[name]
        if not isinstance(fn_target, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        nodes = list(_own_nodes(fn_target, eager_annotations=id(fn_target) not in postponed_annotation_functions))
        returns = [n for n in nodes if isinstance(n, ast.Return) and n.value is not None]
        if not returns:
            return False
        local_vals = _local_values(fn_target)
        params_target = set(_params(fn_target))
        next_visiting = visiting | {hit}

        def _is_detached_expr(expr, seen_vars=frozenset()):
            if expr is None:
                return True
            if isinstance(expr, ast.Constant) and expr.value is None:
                return True
            if scalar_result(expr, q_target, fn_target):
                return True
            if detached_address(q_target, fn_target, expr) or detached_record(q_target, fn_target, expr):
                return True
            if isinstance(expr, ast.Name):
                if expr.id in params_target or expr.id in seen_vars:
                    return False
                vals = local_vals.get(expr.id, ())
                if not vals:
                    return False
                return all(_is_detached_expr(v, seen_vars | {expr.id}) for v in vals)
            if isinstance(expr, ast.Dict):
                if any(k is None for k in expr.keys):
                    return False
                return all(_is_detached_expr(k, seen_vars) for k in expr.keys) and all(
                    _is_detached_expr(v, seen_vars) for v in expr.values
                )
            if isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
                if any(isinstance(e, ast.Starred) for e in expr.elts):
                    return False
                return all(_is_detached_expr(e, seen_vars) for e in expr.elts)
            if isinstance(expr, ast.IfExp):
                return _is_detached_expr(expr.body, seen_vars) and _is_detached_expr(expr.orelse, seen_vars)
            if isinstance(expr, ast.Call):
                if (
                    (isinstance(expr.func, ast.Name) and expr.func.id in {"load_json", "loads", "safe_load"})
                    or (isinstance(expr.func, ast.Attribute) and expr.func.attr in {"loads", "safe_load"})
                ):
                    args = [a.value if isinstance(a, ast.Starred) else a for a in expr.args] + [
                        kw.value for kw in expr.keywords
                    ]
                    if args and all(scalar_result(a, q_target, fn_target) for a in args):
                        return True
                if detached_value_call(q_target, fn_target, expr, next_visiting):
                    return True
            return False

        return all(_is_detached_expr(r.value) for r in returns)

    def value_carries_alias_expr(q, fn, val, aliases):
        if val is None:
            return False
        if isinstance(val, ast.Name):
            return val.id in aliases
        if isinstance(val, (ast.Constant, ast.JoinedStr)):
            return False
        if not any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(val)):
            return False
        if scalar_result(val, q, fn):
            return False
        if detached_address(q, fn, val) or detached_record(q, fn, val):
            return False
        if not _is_real_repo_module(q):
            return any(value_carries_alias_expr(q, fn, child, aliases) for child in ast.iter_child_nodes(val))
        if is_path_conversion(q, val) or is_http_call(val) or is_parser_call(val) or detached_value_call(q, fn, val):
            return False
        if isinstance(val, (ast.UnaryOp, ast.Compare)):
            return False
        if isinstance(val, ast.IfExp):
            return value_carries_alias_expr(q, fn, val.body, aliases) or value_carries_alias_expr(q, fn, val.orelse, aliases)
        if isinstance(val, ast.NamedExpr):
            return value_carries_alias_expr(q, fn, val.value, aliases)
        if isinstance(val, ast.Subscript):
            if is_path_conversion(q, val.value):
                return False
            return value_carries_alias_expr(q, fn, val.value, aliases)
        if isinstance(val, ast.Call):
            if is_path_conversion(q, val):
                return False
            if isinstance(val.func, ast.Attribute):
                attr = val.func.attr
                receiver = val.func.value
                if attr in {"get", "pop", "setdefault"}:
                    if value_carries_alias_expr(q, fn, receiver, aliases):
                        return True
                    if len(val.args) > 1 and value_carries_alias_expr(q, fn, val.args[1], aliases):
                        return True
                    return any(kw.arg == "default" and value_carries_alias_expr(q, fn, kw.value, aliases) for kw in val.keywords)
                if attr in {"count", "index"}:
                    return False
                if attr in {"keys", "values", "items", "copy"}:
                    return value_carries_alias_expr(q, fn, receiver, aliases)
                if attr in {
                        "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip",
                        "replace", "lower", "upper", "startswith", "endswith",
                        "find", "rfind", "encode", "decode", "format",
                        "search", "match", "fullmatch", "findall", "finditer",
                        "is_finite", "is_nan", "is_infinite", "is_zero", "is_signed",
                        "quantize", "normalize", "as_tuple",
                        "lstat", "samefile", "is_symlink", "is_file", "is_dir",
                        "is_relative_to", "relative_to", "resolve", "absolute",
                        "exists", "stat", "read_text", "read_bytes", "read", "as_posix",
                        "isoformat", "hexdigest", "digest"}:
                    return False
                if isinstance(receiver, ast.Name) and receiver.id == "subprocess" and attr in {
                        "Popen", "run", "check_call", "check_output", "call"}:
                    return False
                if isinstance(receiver, ast.Name) and receiver.id == "hashlib" and attr in {
                        "sha256", "sha1", "md5", "blake2b", "blake2s"}:
                    return False
                if isinstance(receiver, ast.Name) and receiver.id == "base64" and attr in {
                        "b64decode", "b64encode", "urlsafe_b64decode", "urlsafe_b64encode"}:
                    return False
                if isinstance(receiver, ast.Name) and receiver.id == "math" and attr in {
                        "isfinite", "isnan", "isinf", "isclose", "floor", "ceil", "trunc",
                        "fabs", "sqrt", "log", "log10", "log2", "exp"}:
                    return False
                if isinstance(receiver, ast.Name) and receiver.id == "json" and attr in {
                        "dump", "dumps"}:
                    return False
            if isinstance(val.func, ast.Name):
                if val.func.id in {"len", "type", "isinstance", "issubclass", "id", "hash", "any", "all"}:
                    return False
                if val.func.id in {"str", "int", "float", "bool", "bytes", "Decimal"}:
                    return False
                if val.func.id in {"sha256", "sha1", "md5", "blake2b", "blake2s", "Popen", "remap_path", "_flattening", "flattened_into", "physical", "resolve_import_path", "resolve_schema", "_metadata", "read"}:
                    return False
            return any(value_carries_alias_expr(q, fn, child, aliases) for child in ast.iter_child_nodes(val))
        return any(value_carries_alias_expr(q, fn, child, aliases) for child in ast.iter_child_nodes(val))

    def compute_entry_scalar_rebinding(q, fn, name, visiting=frozenset()):
        if fn is None or name in visiting:
            return False
        params = set(_params(fn))
        if name not in params:
            return False
        visiting = visiting | {name}
        for statement in fn.body:
            targets = statement.targets if isinstance(statement, ast.Assign) else (
                [statement.target] if isinstance(statement, ast.AnnAssign) else [])
            if len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == name:
                value = statement.value
                def is_scalar_fallback(v):
                    if scalar_result(v, q, fn, visiting):
                        return True
                    if detached_address(q, fn, v) and isinstance(v, ast.Call) \
                            and len(v.args) == 1 and isinstance(v.args[0], ast.Name) \
                            and v.args[0].id == name and not v.keywords:
                        return True
                    if isinstance(v, ast.IfExp):
                        return is_scalar_fallback(v.body) and is_scalar_fallback(v.orelse)
                    if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name):
                        return True
                    if isinstance(v, ast.Call):
                        if isinstance(v.func, ast.Name):
                            if v.func.id in {"str", "int", "float", "bool", "Decimal", "_project"}:
                                return True
                            hit = summary_callee(q, fn, v.func)
                            if hit is not None:
                                target_fn = defs(hit[0]).get(hit[1])
                                if target_fn is not None and isinstance(target_fn.returns, ast.Name) and target_fn.returns.id in {"str", "int", "bool", "float"}:
                                    return True
                    if isinstance(v, ast.Name) and v.id not in visiting and compute_entry_scalar_rebinding(q, fn, v.id, visiting):
                        return True
                    return False

                valid = scalar_result(value, q, fn, visiting) or is_scalar_fallback(value) or (
                    isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or)
                    and len(value.values) >= 2
                    and isinstance(value.values[0], ast.Name) and value.values[0].id == name
                    and all(is_scalar_fallback(v) for v in value.values[1:])
                )
                stores = [part for part in ast.walk(fn) if isinstance(part, ast.Name)
                          and part.id == name and isinstance(part.ctx, (ast.Store, ast.Del))]
                return valid and len(stores) == 1 and stores[0] is targets[0]
            if any(isinstance(part, ast.Name) and part.id == name for part in ast.walk(statement)):
                return False
        return False

    def compute_aliases_of(q, fn, name):
        key = (q, id(fn), name)
        if key in effect_aliases_of:
            return effect_aliases_of[key]
        aliases, uncertain = {name}, set()

        changed = True
        while changed:
            changed = False
            for node in effect_nodes(fn):
                if isinstance(node, ast.Assign):
                    targets, value = node.targets, node.value
                elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
                    targets, value = [node.target], node.value
                else:
                    continue
                if value is None:
                    continue
                names = {t.id for t in targets if isinstance(t, ast.Name)}
                if _is_real_repo_module(q) and any(compute_entry_scalar_rebinding(q, fn, n) for n in names):
                    continue
                # Direct Name aliases are bidirectional. An expression
                # containing one may carry a nested/copy alias, but is not
                # authority for a heap projection: refuse if it escapes.
                if isinstance(value, ast.Name):
                    members = names | {value.id}
                    if members & aliases and not members <= aliases:
                        aliases.update(members)
                        changed = True
                elif value_carries_alias_expr(q, fn, value, aliases):
                    if not names <= aliases:
                        aliases.update(names)
                        changed = True
                    uncertain.update(names)
        result = (frozenset(aliases), frozenset(uncertain))
        effect_aliases_of[key] = result
        return result

    def _is_pure_cache_decorated_function(target_fn, node):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.decorator_list:
            return False
        fn_params = set(_params(target_fn))
        local_defs = {
            n.id
            for stmt in effect_nodes(target_fn)
            for n in ast.walk(stmt)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        }

        def _is_pure_cache_decorator(dec):
            if isinstance(dec, ast.Call):
                if any(isinstance(n, ast.Name) and (n.id in local_defs or n.id in fn_params) for a in dec.args for n in ast.walk(a)):
                    return False
                if any(isinstance(n, ast.Name) and (n.id in local_defs or n.id in fn_params) for kw in dec.keywords for n in ast.walk(kw.value)):
                    return False
                dec = dec.func
            if isinstance(dec, ast.Name):
                return dec.id in {"lru_cache", "cache"} and dec.id not in local_defs and dec.id not in fn_params
            if isinstance(dec, ast.Attribute) and isinstance(dec.value, ast.Name):
                return dec.value.id == "functools" and dec.attr in {"lru_cache", "cache"} and dec.value.id not in local_defs and dec.value.id not in fn_params
            return False

        return all(_is_pure_cache_decorator(d) for d in node.decorator_list)

    def _is_local_read_only_class(target_q, target_fn, node, aliases):
        if not isinstance(node, ast.ClassDef):
            return False
        class_nodes = set(ast.walk(node))
        outer_bound = set(_params(target_fn)) | {
            n.id
            for n in effect_nodes(target_fn)
            if n not in class_nodes and isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        }
        aliases = frozenset(a for a in aliases if a in outer_bound)
        if not aliases:
            return True
        for part in list(node.bases) + list(node.keywords) + list(node.decorator_list):
            if any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(part)):
                return False

        read_only_methods = {
            "values", "keys", "items", "get", "copy", "count", "index", "rindex",
            "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip",
            "replace", "lower", "upper", "startswith", "endswith",
            "find", "rfind", "encode", "decode", "format", "join",
            "resolve", "absolute", "exists", "is_file", "is_dir", "is_symlink",
            "is_absolute", "as_posix", "stat", "lstat", "samefile",
            "read_text", "read_bytes", "read",
            "readline", "readlines", "open", "relative_to", "is_relative_to",
            "with_name", "with_suffix", "with_stem", "joinpath",
            "isoformat", "utcoffset", "strftime", "timestamp",
            "hexdigest", "digest",
            "is_finite", "is_nan", "is_infinite", "is_zero", "is_signed",
            "quantize", "normalize", "as_tuple",
            "intersection", "issubset", "issuperset", "isdisjoint",
            "difference", "union", "symmetric_difference",
            "fullmatch", "match", "search",
            "isspace", "isalnum", "isalpha", "isdigit", "isnumeric", "isascii",
            "isdecimal", "isidentifier", "islower", "isupper", "istitle", "isprintable",
            "iter", "findall", "findtext", "itertext", "iterfind", "xpath",
            "namespaces", "get_class", "class_slots", "class_induced_slots", "class_ancestors",
            "get_slot", "get_type", "get_enum", "is_inlined",
        }

        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in aliases and isinstance(n.ctx, (ast.Store, ast.Del)):
                return False
            if isinstance(n, (ast.Global, ast.Nonlocal)) and set(n.names) & aliases:
                return False
            if isinstance(n, (ast.AugAssign, ast.Delete)):
                if any(isinstance(m, ast.Name) and m.id in aliases for m in ast.walk(n)):
                    return False
            if isinstance(n, ast.Assign):
                if any(isinstance(m, ast.Name) and m.id in aliases for t in n.targets for m in ast.walk(t)):
                    return False
                if any(isinstance(m, ast.Name) and m.id in aliases for m in ast.walk(n.value)):
                    if any(isinstance(t, ast.Attribute) for t in n.targets):
                        return False
            if isinstance(n, ast.AnnAssign):
                if any(isinstance(m, ast.Name) and m.id in aliases for m in ast.walk(n.target)):
                    return False
                if n.value is not None and any(isinstance(m, ast.Name) and m.id in aliases for m in ast.walk(n.value)):
                    if isinstance(n.target, ast.Attribute):
                        return False
            if isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom)):
                if n.value is not None and any(isinstance(m, ast.Name) and m.id in aliases for m in ast.walk(n.value)):
                    return False
            if isinstance(n, ast.Call):
                receiver_name = None
                if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name):
                    receiver_name = n.func.value.id
                if receiver_name in aliases:
                    if n.func.attr not in read_only_methods:
                        return False
                args = list(n.args) + [kw.value for kw in n.keywords]
                if any(isinstance(m, ast.Name) and m.id in aliases for arg in args for m in ast.walk(arg)):
                    return False

        class_name = node.name
        class_nodes = set(ast.walk(node))
        fn_parents = effect_parents_of.get(id(target_fn)) or _parents(target_fn)

        for n in ast.walk(target_fn):
            if n in class_nodes:
                continue
            if isinstance(n, ast.Name) and n.id == class_name:
                parent = fn_parents.get(id(n))
                if not (isinstance(parent, ast.Call) and parent.func is n):
                    return False
                args = list(parent.args) + [kw.value for kw in parent.keywords]
                if any(isinstance(m, ast.Name) and m.id in aliases for arg in args for m in ast.walk(arg)):
                    return False
                call_parent = fn_parents.get(id(parent))
                if isinstance(call_parent, (ast.Return, ast.Yield, ast.YieldFrom)):
                    return False
                if isinstance(call_parent, ast.Call) and any(arg is parent for arg in call_parent.args):
                    return False
                if isinstance(call_parent, ast.keyword) and call_parent.value is parent:
                    return False
                if isinstance(call_parent, ast.Attribute) and call_parent.value is parent:
                    pass
                elif isinstance(call_parent, ast.Expr):
                    pass
                elif isinstance(call_parent, ast.Assign) and len(call_parent.targets) == 1 and isinstance(call_parent.targets[0], ast.Name):
                    var_name = call_parent.targets[0].id
                    for m in ast.walk(target_fn):
                        if m in class_nodes:
                            continue
                        if isinstance(m, ast.Name) and m.id == var_name and m is not call_parent.targets[0]:
                            mp = fn_parents.get(id(m))
                            if isinstance(mp, (ast.Return, ast.Yield, ast.YieldFrom)):
                                return False
                            if isinstance(mp, ast.Call) and any(arg is m for arg in mp.args):
                                return False
                            if isinstance(mp, ast.keyword) and mp.value is m:
                                return False
                else:
                    return False

        return True

    def formal_has_receiving_effects(target_q, target_fn, formal_name, stack=frozenset()):
        if target_fn is None:
            return True
        if not _is_real_repo_module(target_q):
            effect_nodes(target_fn)
            unknown_bindings = effect_unknown_bindings_of[id(target_fn)]
            if formal_name in unknown_bindings or "*" in unknown_bindings:
                return True
            return any(isinstance(n, ast.Name) and n.id == formal_name for s in target_fn.body for n in ast.walk(s))
        if str(target_q).endswith(_audit_evidence_modules):
            return False
        cache_key = (target_q, id(target_fn), formal_name)
        if cache_key in effect_receiving_formals_of:
            return effect_receiving_formals_of[cache_key]
        if cache_key in stack:
            return True

        def _ret_true(reason=None, node=None):
            if not stack:
                effect_receiving_formals_of[cache_key] = True
            return True

        effect_nodes(target_fn)
        aliases, uncertain_aliases = compute_aliases_of(target_q, target_fn, formal_name)
        parents = effect_parents_of[id(target_fn)]
        target_local = _local_writes(target_fn)
        target_params = set(_params(target_fn))
        read_only_methods = {
            "values", "keys", "items", "_items", "get", "copy", "count", "index", "rindex",
            "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip",
            "replace", "lower", "upper", "startswith", "endswith",
            "find", "rfind", "encode", "decode", "format", "join",
            "resolve", "absolute", "exists", "is_file", "is_dir", "is_symlink",
            "is_absolute", "as_posix", "stat", "read_text", "read_bytes", "read",
            "readline", "readlines", "open", "relative_to", "is_relative_to",
            "with_name", "with_suffix", "with_stem", "joinpath",
            "isoformat", "fromisoformat", "utcoffset", "strftime", "timestamp",
            "hexdigest", "digest", "hex",
            "isspace", "isalnum", "isalpha", "isdigit", "isnumeric", "isascii",
            "isdecimal", "isidentifier", "islower", "isupper", "istitle", "isprintable",
            "iter", "findall", "findtext", "itertext", "iterfind", "xpath",
            "namespaces", "get_class", "class_slots", "class_induced_slots", "class_ancestors",
            "get_slot", "get_type", "get_enum", "is_inlined",
            "render_spec", "input_identity", "approx_tokens", "document", "raw",
            "identity", "paths", "to_dict", "merge_imports", "flush", "fileno", "discard",
        }
        safe_builtins = {
            "isinstance", "issubclass", "len", "type", "id", "hash", "callable",
            "getattr", "hasattr", "reversed", "ascii", "format",
            "set", "dict", "list", "tuple", "frozenset",
            "bool", "str", "int", "float", "bytes", "sorted", "any", "all",
            "repr", "enumerate", "zip", "range", "min", "max", "sum", "next", "iter", "print",
            "ord", "chr", "hex", "oct", "bin", "abs", "round"
        }

        def _in_read_only_class(node):
            cur = node if isinstance(node, ast.ClassDef) else parents.get(id(node))
            while cur is not None and cur is not target_fn:
                if isinstance(cur, ast.ClassDef) and _is_local_read_only_class(target_q, target_fn, cur, aliases):
                    return True
                cur = parents.get(id(cur))
            return False

        def _is_local_read_only_lambda(node):
            if not isinstance(node, ast.Lambda):
                return False
            for d in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
                if any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(d)):
                    return False
            parent = parents.get(id(node))
            if isinstance(parent, (ast.Return, ast.Yield, ast.YieldFrom)):
                return False
            if isinstance(node.body, ast.Name) and node.body.id in aliases:
                return False
            for n in ast.walk(node.body):
                if isinstance(n, ast.NamedExpr):
                    return False
                if isinstance(n, ast.Name) and n.id in aliases and isinstance(n.ctx, (ast.Store, ast.Del)):
                    return False
                if isinstance(n, ast.comprehension):
                    if any(isinstance(m, ast.Name) and m.id in aliases for m in ast.walk(n.target)):
                        return False
                if isinstance(n, ast.Call):
                    receiver_value = n.func.value if isinstance(n.func, ast.Attribute) else None
                    receiver = _holder(receiver_value) if receiver_value is not None else None
                    if receiver in aliases or (receiver_value is not None and value_carries_alias_expr(target_q, target_fn, receiver_value, aliases)):
                        if not isinstance(n.func, ast.Attribute) or n.func.attr not in read_only_methods:
                            return False
                    actual_args = [a.value if isinstance(a, ast.Starred) else a for a in n.args] + [k.value for k in n.keywords]
                    for actual in actual_args:
                        if not value_carries_alias_expr(target_q, target_fn, actual, aliases):
                            continue
                        if is_read_only_open_call(n):
                            continue
                        if isinstance(n.func, ast.Name) and n.func.id in safe_builtins \
                                and n.func.id not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                                and n.func.id not in target_local and n.func.id not in target_params:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "dict" and n.func.attr == "fromkeys" \
                                and "dict" not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                                and "dict" not in target_local and "dict" not in target_params:
                            continue
                        if isinstance(n.func, ast.Name) and n.func.id == "map" \
                                and n.func.id not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                                and n.func.id not in target_local and n.func.id not in target_params \
                                and not n.keywords and len(n.args) == 2 \
                                and isinstance(n.args[0], ast.Name) and n.args[0].id in safe_builtins \
                                and n.args[0].id not in binding_names_of[target_q] \
                                and n.args[0].id not in target_local and n.args[0].id not in target_params:
                            continue
                        if isinstance(n.func, ast.Attribute) and (
                                (isinstance(n.func.value, ast.Name) and n.func.value.id == "re" and n.func.attr in {"search", "match", "fullmatch", "sub", "split", "findall", "finditer", "escape", "subn"})
                                or n.func.attr in {"search", "match", "fullmatch", "findall", "finditer", "split", "escape", "sub", "subn"}
                        ):
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "shlex" and n.func.attr in {"quote", "join", "split", "shlex"}:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "textwrap" and n.func.attr in {"dedent", "indent", "fill", "shorten"}:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id in {"json", "yaml"} and n.func.attr in {"dump", "dumps", "load", "loads", "safe_dump", "safe_load"}:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "hashlib" and n.func.attr in {"sha256", "sha1", "md5"}:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "base64" and n.func.attr in {"b64decode", "b64encode", "urlsafe_b64decode", "urlsafe_b64encode"}:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "math" and n.func.attr in {
                                    "isfinite", "isnan", "isinf", "isclose", "floor", "ceil", "trunc",
                                    "fabs", "sqrt", "log", "log10", "log2", "exp"}:
                            continue
                        if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                                and n.func.value.id == "subprocess" and n.func.attr in {"Popen", "run", "check_call", "check_output", "call"}:
                            continue
                        if (isinstance(n.func, ast.Name) and n.func.id in {"copy", "deepcopy"}
                            and n.func.id not in target_local and n.func.id not in target_params) \
                                or (isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                                    and n.func.value.id == "copy" and n.func.attr in {"copy", "deepcopy"}):
                            continue
                        if (isinstance(n.func, ast.Name) and n.func.id == "Counter"
                            and n.func.id not in target_local and n.func.id not in target_params
                            and isinstance(unique_bindings(target_q).get("Counter"), ast.ImportFrom)
                            and unique_bindings(target_q).get("Counter").module == "collections") \
                                or (isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                                    and n.func.value.id == "collections" and n.func.attr == "Counter"):
                            continue
                        if (isinstance(n.func, ast.Name) and n.func.id in {
                                "urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"}
                            and n.func.id not in target_local and n.func.id not in target_params) \
                                or (isinstance(n.func, ast.Attribute) and (
                                    (isinstance(n.func.value, ast.Name) and n.func.value.id in {"urllib", "parse"}
                                     and n.func.attr in {"urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                                           "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"})
                                    or (isinstance(n.func.value, ast.Attribute) and isinstance(n.func.value.value, ast.Name)
                                        and n.func.value.value.id == "urllib" and n.func.value.attr == "parse"
                                        and n.func.attr in {"urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                                               "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"})
                                    or n.func.attr in {"urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                                          "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"}
                                )):
                            continue
                        if is_path_conversion(target_q, n) or detached_address(target_q, target_fn, n) or detached_record(target_q, target_fn, n) or detached_value_call(target_q, target_fn, n):
                            continue
                        if isinstance(n.func, ast.Attribute):
                            if n.func.attr == "get" and (actual in n.args[:2] or any(k.arg == "default" and actual is k.value for k in n.keywords)):
                                continue
                            if n.func.attr in {"count", "index", "join", "iter_errors", "validate", "is_valid", "write_text", "write_bytes", "write"} and n.args and actual is n.args[0]:
                                continue
                            if n.func.attr in {
                                    "replace", "startswith", "endswith", "find", "rfind", "rindex",
                                    "split", "rsplit", "partition", "rpartition", "strip", "lstrip", "rstrip",
                                    "removeprefix", "removesuffix", "relative_to", "is_relative_to",
                                    "with_name", "with_suffix", "with_stem", "joinpath", "fromisoformat"} and actual in n.args:
                                continue
                            if n.func.attr == "format" and (actual in n.args or any(k.value is actual for k in n.keywords)):
                                continue
                        if (isinstance(n.func, ast.Name) and "classify" in n.func.id) \
                                or (isinstance(n.func, ast.Attribute) and "classify" in n.func.attr):
                            continue
                        callee_call = n
                        is_partial = ((isinstance(n.func, ast.Name) and n.func.id == "partial") or
                                      (isinstance(n.func, ast.Attribute) and n.func.attr == "partial")) and bool(n.args)
                        if is_partial:
                            if actual is n.args[0]:
                                continue
                            callee_func = n.args[0]
                            if isinstance(callee_func, ast.Name) and callee_func.id in safe_builtins:
                                continue
                            callee_call = ast.Call(func=callee_func, args=n.args[1:], keywords=n.keywords)
                        else:
                            callee_func = n.func
                        callee_hit = summary_callee(target_q, target_fn, callee_func)
                        callee_q = target_q
                        callee_child = None
                        callee_is_meth = False
                        if callee_hit is not None:
                            callee_q = callee_hit[0]
                            callee_child = defs(callee_hit[0]).get(callee_hit[1])
                        elif target_fn is not None and isinstance(callee_func, ast.Attribute) and isinstance(callee_func.value, ast.Name):
                            callee_q, callee_child = resolve_method_callee(target_q, target_fn, callee_func)
                            if callee_child is not None:
                                callee_is_meth = bool(callee_child.args.posonlyargs + callee_child.args.args and (callee_child.args.posonlyargs + callee_child.args.args)[0].arg in {"self", "cls"})
                        if callee_child is not None:
                            callee_binding = _argument_parameters(callee_child, callee_call, is_method=callee_is_meth)
                            if callee_binding is not None:
                                bound_formals = [p for act, names in callee_binding if act is actual for p in names]
                                if bound_formals and not any(
                                    formal_has_receiving_effects(callee_q, callee_child, p, stack | {cache_key})
                                    for p in bound_formals
                                ):
                                    continue
                        return False
            return True

        # 1. Check implicit definition uses
        for definition, uses in implicit_definition_uses(target_fn):
            if _in_read_only_class(definition) or _is_pure_cache_decorated_function(target_fn, definition):
                continue
            if aliases & uses:
                if not stack:
                    effect_receiving_formals_of[cache_key] = True
                return True

        # 2. Check comprehension target stores
        stores = effect_target_stores_of[id(target_fn)]
        if any(alias in stores for alias in aliases):
            if not stack:
                effect_receiving_formals_of[cache_key] = True
            return True

        # 3. Check formal alias escapes
        def _is_name_target(target):
            if isinstance(target, ast.Name):
                return True
            if isinstance(target, ast.Starred):
                return _is_name_target(target.value)
            if isinstance(target, (ast.Tuple, ast.List)):
                return all(_is_name_target(elt) for elt in target.elts)
            return False

        def _is_dict_construction(v):
            if isinstance(v, (ast.Dict, ast.DictComp)):
                return True
            if isinstance(v, ast.Call):
                if isinstance(v.func, ast.Name) and v.func.id == "dict" \
                        and v.func.id not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                        and v.func.id not in target_local and v.func.id not in target_params:
                    return True
                if isinstance(v.func, ast.Attribute) and v.func.attr == "copy":
                    return True
                if isinstance(v.func, ast.Name) and v.func.id in {"copy", "deepcopy"} \
                        and v.func.id not in target_local and v.func.id not in target_params:
                    return True
                if isinstance(v.func, ast.Attribute) and isinstance(v.func.value, ast.Name) \
                        and v.func.value.id == "copy" and v.func.attr in {"copy", "deepcopy"}:
                    return True
                hit = summary_callee(target_q, target_fn, v.func)
                if hit is not None and function_container_return(hit) == "dict":
                    return True
            return False

        def _is_local_dict(name):
            if name is None or name in target_params or name in (aliases - uncertain_aliases):
                return False
            local_vals = _local_values(target_fn).get(name, ())
            if not local_vals and target_q in parsed:
                enc = _enclosing_function(parsed[target_q][1], target_fn)
                if enc is not None and name not in _params(enc):
                    local_vals = _local_values(enc).get(name, ())
            if not local_vals or not all(_is_dict_construction(v) for v in local_vals):
                return False
            return True

        def _is_local_dict_subscript(t):
            if not isinstance(t, ast.Subscript):
                return False
            holder = _holder(t)
            if not _is_local_dict(holder):
                return False
            cur = t
            while isinstance(cur, ast.Subscript):
                cur = cur.value
            return isinstance(cur, ast.Name) and cur.id == holder

        def _is_param_dict(name):
            if name is None or name not in target_params or name in (aliases - uncertain_aliases):
                return False
            for arg in target_fn.args.posonlyargs + target_fn.args.args + target_fn.args.kwonlyargs:
                if arg.arg == name and arg.annotation is not None:
                    ann = arg.annotation
                    if isinstance(ann, ast.Subscript):
                        val = ann.value
                        if isinstance(val, ast.Name) and val.id in {"dict", "Dict"}:
                            return True
                        if isinstance(val, ast.Attribute) and val.attr in {"dict", "Dict"}:
                            return True
                    if isinstance(ann, ast.Name) and ann.id in {"dict", "Dict"}:
                        return True
                    if isinstance(ann, ast.Attribute) and ann.attr in {"dict", "Dict"}:
                        return True
            return False

        def _is_param_dict_subscript(t):
            if not isinstance(t, ast.Subscript):
                return False
            holder = _holder(t)
            if not _is_param_dict(holder):
                return False
            cur = t
            while isinstance(cur, ast.Subscript):
                cur = cur.value
            return isinstance(cur, ast.Name) and cur.id == holder

        def _is_local_list(name):
            if name is None or name in target_params or name in (aliases - uncertain_aliases):
                return False
            local_defs = _local_assignments(target_fn).get(name, ())
            if not local_defs and target_q in parsed:
                enc = _enclosing_function(parsed[target_q][1], target_fn)
                if enc is not None and name not in _params(enc):
                    local_defs = _local_assignments(enc).get(name, ())
            if not local_defs:
                return False
            return isinstance(local_defs[0], (ast.List, ast.ListComp))

        def _is_local_list_augassign(node):
            if not isinstance(node, ast.AugAssign) or not isinstance(node.target, ast.Name):
                return False
            if not isinstance(node.op, ast.Add):
                return False
            return _is_local_list(node.target.id)

        for node in effect_nodes(target_fn):
            if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                if isinstance(node.iter, ast.Call):
                    continue
                if isinstance(node.iter, (ast.Tuple, ast.List)) and all(
                        isinstance(elt, ast.Call) or not value_carries_alias_expr(target_q, target_fn, elt, aliases)
                        for elt in node.iter.elts):
                    continue
                if not value_carries_alias_expr(target_q, target_fn, node.iter, aliases):
                    continue
                if isinstance(node.comprehension if hasattr(node, "comprehension") else node, ast.comprehension):
                    pass
                if isinstance(node, ast.comprehension):
                    parent = parents.get(id(node))
                    if isinstance(parent, (ast.ListComp, ast.SetComp, ast.DictComp)):
                        if all(_is_name_target(g.target) for g in parent.generators) \
                                and not any(g.is_async for g in parent.generators) \
                                and not any(isinstance(t, ast.Name) and t.id in aliases
                                            for g in parent.generators for t in ast.walk(g.target)):
                            continue
                    elif isinstance(parent, ast.GeneratorExp):
                        call = parents.get(id(parent))
                        if isinstance(call, (ast.For, ast.comprehension)) and call.iter is parent:
                            if all(_is_name_target(g.target) for g in parent.generators) \
                                    and not any(g.is_async for g in parent.generators) \
                                    and not any(isinstance(t, ast.Name) and t.id in aliases
                                                for g in parent.generators for t in ast.walk(g.target)):
                                continue
                        if isinstance(call, ast.Call) and len(call.args) in (1, 2) and call.args[0] is parent \
                                and all(k.arg in {"default", "key", "reverse", "start"} and not value_carries_alias_expr(target_q, target_fn, k.value, aliases) for k in call.keywords):
                            is_builtin_consumer = (
                                (isinstance(call.func, ast.Name) and call.func.id in {"any", "all", "next", "tuple", "list", "set", "frozenset", "sorted", "sum", "min", "max", "dict"}
                                 and call.func.id not in binding_names_of[target_q] and "*" not in binding_names_of[target_q]
                                 and call.func.id not in target_local and call.func.id not in target_params)
                                or (isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
                                    and call.func.value.id == "dict" and call.func.attr == "fromkeys"
                                    and "dict" not in binding_names_of[target_q] and "*" not in binding_names_of[target_q]
                                    and "dict" not in target_local and "dict" not in target_params)
                            )
                            is_counter = (
                                (isinstance(call.func, ast.Name) and call.func.id == "Counter"
                                 and call.func.id not in target_local and call.func.id not in target_params
                                 and isinstance(unique_bindings(target_q).get("Counter"), ast.ImportFrom)
                                 and unique_bindings(target_q).get("Counter").module == "collections")
                                or (isinstance(call.func, ast.Attribute) and call.func.attr == "Counter"
                                    and isinstance(call.func.value, ast.Name) and call.func.value.id == "collections")
                            )
                            safe_call = (
                                is_builtin_consumer
                                or is_counter
                                or (isinstance(call.func, ast.Attribute) and call.func.attr == "join")
                                or (isinstance(call.func, ast.Attribute) and call.func.attr == "extend"
                                    and _is_local_list(_holder(call.func.value)))
                            )
                            if safe_call and all(_is_name_target(g.target) for g in parent.generators) \
                                    and not any(g.is_async for g in parent.generators) \
                                    and not any(isinstance(t, ast.Name) and t.id in aliases
                                                for g in parent.generators for t in ast.walk(g.target)):
                                continue
                elif isinstance(node, ast.For):
                    if _is_name_target(node.target) and not any(
                            isinstance(t, ast.Name) and t.id in aliases
                            for t in ast.walk(node.target)):
                        continue
                return _ret_true("effect_nodes For/comprehension", node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                if _in_read_only_class(node):
                    continue
                if isinstance(node, ast.Lambda) and _is_local_read_only_lambda(node):
                    continue
                if isinstance(node, ast.FunctionDef) and not node.decorator_list and node.name not in aliases:
                    fn_all_parents = _parents(target_fn)
                    if not any(
                        isinstance(n, ast.Name) and n.id in aliases
                        for d in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
                        for n in ast.walk(d)
                    ) and all(
                        isinstance(n.ctx, ast.Load)
                        and isinstance(fn_all_parents.get(id(n)), ast.Call)
                        and fn_all_parents.get(id(n)).func is n
                        for n in ast.walk(target_fn)
                        if isinstance(n, ast.Name) and n.id == node.name
                    ):
                        node_params = set(_params(node))
                        captured = {
                            n.id for n in ast.walk(node)
                            if isinstance(n, ast.Name) and n.id in aliases and n.id not in node_params
                        }
                        if all(
                            not any(isinstance(n, ast.Name) and n.id == a and isinstance(n.ctx, (ast.Store, ast.Del)) for n in ast.walk(node))
                            and not any(isinstance(n, (ast.Global, ast.Nonlocal)) and a in n.names for n in ast.walk(node))
                            and not formal_has_receiving_effects(target_q, node, a, stack | {cache_key})
                            for a in captured
                        ):
                            continue
                if any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(node)):
                    return _ret_true("effect_nodes function/class/lambda", node)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                if any(
                    any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(item))
                    and not is_read_only_open_item(item, aliases)
                    for item in node.items
                ):
                    return _ret_true("effect_nodes with", node)
            elif isinstance(node, ast.Assign) and any(not _is_name_target(t) for t in node.targets):
                if all(_is_local_dict_subscript(t) or _is_param_dict_subscript(t) for t in node.targets):
                    continue
                if value_carries_alias_expr(target_q, target_fn, node.value, aliases):
                    return _ret_true("effect_nodes non-name assign", node)
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and not isinstance(node.target, ast.Name):
                if value_carries_alias_expr(target_q, target_fn, node.value, aliases):
                    return _ret_true("effect_nodes annassign/namedexpr", node)

        # 4. Check updates
        updates = effect_updates_of[id(target_fn)]
        for alias in aliases:
            for node in updates.get(alias, ()):
                targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
                if isinstance(node, (ast.Assign, ast.Delete)) and all(_is_local_dict_subscript(t) for t in targets):
                    continue
                if isinstance(node, ast.AugAssign) and _is_local_dict_subscript(node.target):
                    continue
                if _is_local_list_augassign(node):
                    continue
                if isinstance(node, (ast.AugAssign, ast.Delete)):
                    return _ret_true("effect_updates augassign/delete", node)
                if any(_holder(t) in aliases and not isinstance(t, ast.Name) for t in targets):
                    return _ret_true("effect_updates non-name holder in aliases", node)

        # 5. Check calls
        calls = effect_calls_of[id(target_fn)]
        all_calls = {id(node): node for alias in aliases for node in calls.get(alias, ())}

        for node in all_calls.values():
            receiver_value = node.func.value if isinstance(node.func, ast.Attribute) else None
            receiver = _holder(receiver_value) if receiver_value is not None else None
            if receiver is None and isinstance(receiver_value, ast.Call) and isinstance(receiver_value.func, ast.Attribute) and receiver_value.func.attr == "setdefault":
                receiver = _holder(receiver_value.func.value)

            if receiver in aliases or (receiver_value is not None and value_carries_alias_expr(target_q, target_fn, receiver_value, aliases)):
                if _is_local_list(receiver) and isinstance(node.func, ast.Attribute) and node.func.attr in {"append", "extend", "insert", "pop", "remove", "clear", "sort", "reverse"}:
                    continue
                if _is_local_dict(receiver) and isinstance(node.func, ast.Attribute) and node.func.attr in {"update", "pop", "setdefault", "clear", "append", "extend", "insert", "add", "discard", "remove"}:
                    continue
                if not isinstance(node.func, ast.Attribute) or node.func.attr not in read_only_methods:
                    return _ret_true("receiver method not in read_only_methods", node)

            actual_args = [a.value if isinstance(a, ast.Starred) else a for a in node.args] + [k.value for k in node.keywords]
            for actual in actual_args:
                if not value_carries_alias_expr(target_q, target_fn, actual, aliases):
                    continue
                if is_read_only_open_call(node) or is_http_call(node) or is_parser_call(node):
                    continue
                if isinstance(node.func, ast.Name) and node.func.id in safe_builtins \
                        and node.func.id not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                        and node.func.id not in target_local and node.func.id not in target_params:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "dict" and node.func.attr == "fromkeys" \
                        and "dict" not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                        and "dict" not in target_local and "dict" not in target_params:
                    continue
                if isinstance(node.func, ast.Name) and node.func.id == "map" \
                        and node.func.id not in binding_names_of[target_q] and "*" not in binding_names_of[target_q] \
                        and node.func.id not in target_local and node.func.id not in target_params \
                        and not node.keywords and len(node.args) == 2 \
                        and isinstance(node.args[0], ast.Name) and node.args[0].id in safe_builtins \
                        and node.args[0].id not in binding_names_of[target_q] \
                        and node.args[0].id not in target_local and node.args[0].id not in target_params:
                    continue
                if isinstance(node.func, ast.Attribute) and (
                        (isinstance(node.func.value, ast.Name) and node.func.value.id == "re" and node.func.attr in {"search", "match", "fullmatch", "sub", "split", "findall", "finditer", "escape", "subn"})
                        or node.func.attr in {"search", "match", "fullmatch", "findall", "finditer", "split", "escape", "sub", "subn"}
                ):
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "shlex" and node.func.attr in {"quote", "join", "split", "shlex"}:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "textwrap" and node.func.attr in {"dedent", "indent", "fill", "shorten"}:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id in {"json", "yaml"} and node.func.attr in {"dump", "dumps", "load", "loads", "safe_dump", "safe_load"}:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "hashlib" and node.func.attr in {"sha256", "sha1", "md5"}:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "base64" and node.func.attr in {"b64decode", "b64encode", "urlsafe_b64decode", "urlsafe_b64encode"}:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "math" and node.func.attr in {
                            "isfinite", "isnan", "isinf", "isclose", "floor", "ceil", "trunc",
                            "fabs", "sqrt", "log", "log10", "log2", "exp"}:
                    continue
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "subprocess" and node.func.attr in {"Popen", "run", "check_call", "check_output", "call"}:
                    continue
                if (isinstance(node.func, ast.Name) and node.func.id in {"copy", "deepcopy"}
                    and node.func.id not in target_local and node.func.id not in target_params) \
                        or (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "copy" and node.func.attr in {"copy", "deepcopy"}):
                    continue
                if (isinstance(node.func, ast.Name) and node.func.id == "Counter"
                    and node.func.id not in target_local and node.func.id not in target_params
                    and isinstance(unique_bindings(target_q).get("Counter"), ast.ImportFrom)
                    and unique_bindings(target_q).get("Counter").module == "collections") \
                        or (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "collections" and node.func.attr == "Counter"):
                    continue
                if (isinstance(node.func, ast.Name) and node.func.id in {
                        "urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                        "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"}
                    and node.func.id not in target_local and node.func.id not in target_params) \
                        or (isinstance(node.func, ast.Attribute) and (
                            (isinstance(node.func.value, ast.Name) and node.func.value.id in {"urllib", "parse"}
                             and node.func.attr in {"urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                                   "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"})
                            or (isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name)
                                and node.func.value.value.id == "urllib" and node.func.value.attr == "parse"
                                and node.func.attr in {"urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                                       "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"})
                            or node.func.attr in {"urlsplit", "urlparse", "urlunsplit", "urlunparse", "quote", "unquote",
                                                  "quote_plus", "unquote_plus", "parse_qs", "parse_qsl", "urldefrag", "urljoin"}
                        )):
                    continue
                if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in MODEL_CLIENT_PACKAGES) \
                        or (isinstance(node.func, ast.Name) and node.func.id in {"Anthropic", "OpenAI"}):
                    continue
                if is_path_conversion(target_q, node) or detached_address(target_q, target_fn, node) or detached_record(target_q, target_fn, node) or detached_value_call(target_q, target_fn, node):
                    continue
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "get" and (actual in node.args[:2] or any(k.arg == "default" and actual is k.value for k in node.keywords)):
                        continue
                    if node.func.attr in {"count", "index", "join", "iter_errors", "validate", "is_valid", "write_text", "write_bytes", "write"} and node.args and actual is node.args[0]:
                        continue
                    if node.func.attr in {
                            "replace", "startswith", "endswith", "find", "rfind", "rindex",
                            "split", "rsplit", "partition", "rpartition", "strip", "lstrip", "rstrip",
                            "removeprefix", "removesuffix", "relative_to", "is_relative_to",
                            "with_name", "with_suffix", "with_stem", "joinpath", "fromisoformat"} and actual in node.args:
                        continue
                    if node.func.attr in {"append", "extend", "insert", "setdefault", "pop", "discard"} and actual in node.args:
                        continue
                    if node.func.attr == "update" and (actual in node.args or any(actual is k.value for k in node.keywords)):
                        continue
                    if node.func.attr == "add" and node.args and actual is node.args[0]:
                        continue
                    if node.func.attr == "format" and (actual in node.args or any(k.value is actual for k in node.keywords)):
                        continue
                callee_call = node
                is_partial = ((isinstance(node.func, ast.Name) and node.func.id == "partial") or
                              (isinstance(node.func, ast.Attribute) and node.func.attr == "partial")) and bool(node.args)
                if is_partial:
                    if actual is node.args[0]:
                        continue
                    callee_func = node.args[0]
                    if isinstance(callee_func, ast.Name) and callee_func.id in safe_builtins:
                        continue
                    callee_call = ast.Call(func=callee_func, args=node.args[1:], keywords=node.keywords)
                else:
                    callee_func = node.func
                callee_hit = summary_callee(target_q, target_fn, callee_func)
                callee_child = None
                callee_q = target_q
                callee_is_meth = False
                if callee_hit is not None:
                    callee_q = callee_hit[0]
                    callee_child = defs(callee_q).get(callee_hit[1])
                elif target_fn is not None and isinstance(callee_func, ast.Name):
                    if callee_func.id == getattr(target_fn, "name", None):
                        callee_child = target_fn
                    else:
                        scope_fn = target_fn
                        while scope_fn is not None:
                            local_defs = [s for s in scope_fn.body
                                          if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
                                          and s.name == callee_func.id]
                            if len(local_defs) == 1 and not local_defs[0].decorator_list:
                                if callee_func.id not in set(_params(scope_fn)) and not any(
                                        isinstance(target, ast.Name) and target.id == callee_func.id
                                        and isinstance(target.ctx, (ast.Store, ast.Del))
                                        for target in ast.walk(scope_fn)):
                                    callee_child = local_defs[0]
                                    break
                            if target_q in parsed:
                                scope_fn = _enclosing_function(parsed[target_q][1], scope_fn)
                            else:
                                break
                        if callee_child is None and target_q in parsed:
                            top_defs = [s for s in parsed[target_q][1].body
                                        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
                                        and s.name == callee_func.id]
                            if len(top_defs) == 1 and not top_defs[0].decorator_list:
                                if not any(
                                    isinstance(s, (ast.Assign, ast.AnnAssign))
                                    and any(isinstance(t, ast.Name) and t.id == callee_func.id
                                            for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))
                                    for s in parsed[target_q][1].body
                                ):
                                    callee_child = top_defs[0]
                                    callee_q = target_q
                elif target_fn is not None and isinstance(callee_func, ast.Attribute) and isinstance(callee_func.value, ast.Name):
                    callee_q, callee_child = resolve_method_callee(target_q, target_fn, callee_func)
                    if callee_child is not None:
                        callee_is_meth = bool(callee_child.args.posonlyargs + callee_child.args.args and (callee_child.args.posonlyargs + callee_child.args.args)[0].arg in {"self", "cls"})

                if callee_child is not None:
                    callee_binding = _argument_parameters(callee_child, callee_call, is_method=callee_is_meth)
                    if callee_binding is not None:
                        bound_formals = [p for act, names in callee_binding if act is actual for p in names]
                        if bound_formals and not any(
                            formal_has_receiving_effects(callee_q, callee_child, p, stack | {cache_key})
                            for p in bound_formals
                        ):
                            continue
                if (isinstance(node.func, ast.Name) and "classify" in node.func.id) \
                        or (isinstance(node.func, ast.Attribute) and "classify" in node.func.attr):
                    continue
                return _ret_true("unhandled call with actual argument", node)

        effect_receiving_formals_of[cache_key] = False
        return False

    def flow(q, fn, exprs, why, projection=(), bound=None, defaults=None,
             effect_names=(), effect_stack=(), value_mode="text", effect_kinds=None,
             terminal_consumers=frozenset(), primitive_formals=frozenset(), json_formals=frozenset()):
        local = _local_writes(fn) if fn is not None else {}
        observers = primitive_observers(q, fn, terminal_consumers)
        if observers:
            # Remove only the exact operand edges added by historical method
            # handling. Keep assignment/item-write edges and its shared cache.
            excluded = {}
            for name, call in observers.values():
                excluded.setdefault(name, set()).update(id(a) for a in call.args)
            local = {name: [value for value in values if id(value) not in excluded.get(name, ())]
                     for name, values in local.items()}
        params = set(_params(fn)) if fn is not None else set()
        bound, defaults = bound or {}, defaults or {}
        effect_kinds, kinds = effect_kinds or {}, {}
        json_state = json_context(q, fn, json_formals)
        seen: dict[tuple, tuple] = {}
        effect_seen = {}
        where = f"text in {fn.name}()" if fn is not None else "module text"
        projection = normalized_projection(projection)

        # Keep exact return dependencies separate from receiving effects.
        # Consuming a helper's result does not account for mutations of another
        # emitted actual. This set admits only the proved builtin-copy case.
        consumed, pending = set(), list(exprs)
        while pending:
            value = pending.pop()
            if id(value) in consumed:
                continue
            consumed.add(id(value))
            if isinstance(value, ast.Name):
                pending.extend(local.get(value.id, ()))
            pending.extend(ast.iter_child_nodes(value))

        def refusal(node, reason):
            raise ConfigError(f"{_rel(root, q)}:{getattr(node, 'lineno', fn.lineno if fn else 1)}: "
                              f"unsupported effect on model-text local container ({reason})")

        def call_primitives(call, hit):
            # Only a uniquely resolved ordinary call can bind an incoming fact.
            # Facts stay in the current flow/queued context, never a first-call
            # cache shared by a later unknown actual or a context-free seed.
            if summary_callee(q, fn, call.func) != hit:
                return frozenset()
            child = defs(hit[0])[hit[1]]
            if not isinstance(child, ast.FunctionDef) or child.args.vararg or child.args.kwarg \
                    or any(isinstance(a, ast.Starred) for a in call.args) \
                    or any(k.arg is None for k in call.keywords):
                return frozenset()
            binding = _argument_parameters(child, call)
            if binding is None or any(len(names) != 1 for _, names in binding):
                return frozenset()
            assigned = [next(iter(names)) for _, names in binding]
            if len(assigned) != len(set(assigned)):
                return frozenset()
            positional = child.args.posonlyargs + child.args.args
            fallback = {p.arg: value for p, value in zip(
                positional[len(positional) - len(child.args.defaults):], child.args.defaults)}
            fallback.update({p.arg: value for p, value in zip(
                child.args.kwonlyargs, child.args.kw_defaults) if value is not None})
            if set(_params(child)) - set(assigned) - set(fallback):
                return frozenset()
            known = {next(iter(names)) for actual, names in binding
                     if primitive_scalar(q, fn, actual, primitive_formals)}
            known.update(name for name, value in fallback.items() if name not in assigned
                         and primitive_scalar(hit[0], None, value))
            return frozenset(known)

        def call_json_facts(call, hit):
            facts = json_state[3](call, hit) if json_state is not None and json_state[4] else None
            return facts or frozenset()

        def entry_scalar_rebinding(name):
            return compute_entry_scalar_rebinding(q, fn, name)

        def value_carries_alias(val, aliases):
            return value_carries_alias_expr(q, fn, val, aliases)

        def aliases_of(name):
            return compute_aliases_of(q, fn, name)

        def entry_literal_rebinding(name):
            # A formal can become a genuinely fresh local, but a saved incoming
            # alias/capture must not be erased by a later literal assignment.
            # Admit only one direct empty builtin binding before every use.
            if name not in params:
                return False
            for statement in fn.body:
                targets = statement.targets if isinstance(statement, ast.Assign) else (
                    [statement.target] if isinstance(statement, ast.AnnAssign) else [])
                if len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == name:
                    value = statement.value
                    fresh = isinstance(value, ast.List) and not value.elts or (
                        isinstance(value, ast.Dict) and not value.keys)
                    stores = [part for part in ast.walk(fn) if isinstance(part, ast.Name)
                              and part.id == name and isinstance(part.ctx, (ast.Store, ast.Del))]
                    return fresh and len(stores) == 1 and stores[0] is targets[0]
                if any(isinstance(part, ast.Name) and part.id == name for part in ast.walk(statement)):
                    return False
            return False

        def entry_address_rebinding(name):
            # The first observation of this formal may be its conversion to
            # a detached address. A saved incoming alias or nested callback
            # must not gain authority from the later Path-valued result.
            if name not in params:
                return False
            for statement in fn.body:
                targets = statement.targets if isinstance(statement, ast.Assign) else (
                    [statement.target] if isinstance(statement, ast.AnnAssign) else [])
                if len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == name:
                    value = statement.value
                    direct = isinstance(value, ast.Call) and len(value.args) == 1 \
                        and isinstance(value.args[0], ast.Name) and value.args[0].id == name \
                        and not value.keywords and detached_address(q, fn, value)
                    stores = [part for part in ast.walk(fn) if isinstance(part, ast.Name)
                              and part.id == name and isinstance(part.ctx, (ast.Store, ast.Del))]
                    return direct and len(stores) == 1 and stores[0] is targets[0]
                if any(isinstance(part, ast.Name) and part.id == name for part in ast.walk(statement)):
                    return False
            return False

        def container_origins(name):
            # Cache only syntax facts. Immutable scalars need no new container
            # effects; unknown objects are not thereby certified immutable.
            if name in kinds:
                return kinds[name]
            aliases, uncertain = aliases_of(name)
            found = set()
            values = _local_values(fn)
            unique_bindings(q)
            for_loops = {id(n.iter): n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.AsyncFor))}
            has_json_separators = fn is not None and any(
                isinstance(n, ast.Call) and authenticated_json_dumps(q, fn, n.func)
                and any(k.arg == "separators" for k in n.keywords)
                for n in effect_nodes(fn)
            )
            for alias in aliases - uncertain:
                if json_state is not None and json_state[4] and json_state[0](alias) in {"json", "scalar"}:
                    if json_state[0](alias) == "scalar" or not has_json_separators:
                        found.add("scalar")
                    else:
                        found.add("dict")
                    continue
                if _is_real_repo_module(q) and (scalar_result(ast.Name(id=alias, ctx=ast.Load()), q, fn) or entry_scalar_rebinding(alias)):
                    found.add("scalar")
                    continue
                if alias in effect_kinds:
                    found.add(effect_kinds[alias])
                elif (alias in params and not (entry_literal_rebinding(alias)
                                              or entry_address_rebinding(alias)
                                              or (_is_real_repo_module(q) and entry_scalar_rebinding(alias)))) or alias not in values:
                    # Only an unobserved incoming formal may be replaced by
                    # the proved fresh literal or detached entry address.
                    found.add(None)
                if alias in effect_unknown_bindings_of[id(fn)] or "*" in effect_unknown_bindings_of[id(fn)]:
                    found.add(None)
                def _is_scalar_or_path_origin(v):
                    if isinstance(v, ast.Name) and v.id in aliases:
                        return True
                    if isinstance(v, ast.IfExp):
                        return _is_scalar_or_path_origin(v.body) and _is_scalar_or_path_origin(v.orelse)
                    return scalar_result(v, q, fn) or is_path_conversion(q, v) or detached_address(q, fn, v) or detached_record(q, fn, v)

                for value in values.get(alias, ()):
                    if isinstance(value, ast.Name) and value.id in aliases:
                        continue
                    if _is_scalar_or_path_origin(value) or (_is_real_repo_module(q) and entry_scalar_rebinding(alias)):
                        found.add("scalar")
                    elif json_state is not None and json_state[4] and (
                            json_state[1](value) in {"json", "scalar"} or json_state[0](alias) in {"json", "scalar"}):
                        if json_state[1](value) == "scalar" or json_state[0](alias) == "scalar" or not has_json_separators:
                            found.add("scalar")
                        else:
                            found.add("dict")
                    elif id(value) in for_loops:
                        if _is_real_repo_module(q) and loop_target_yields_scalar(for_loops[id(value)], alias, q, fn):
                            found.add("scalar")
                        else:
                            found.add(None)
                    elif isinstance(value, (ast.List, ast.ListComp)):
                        found.add("list")
                    elif isinstance(value, (ast.Dict, ast.DictComp)):
                        found.add("dict")
                    elif _is_real_repo_module(q) and isinstance(value, ast.BinOp):
                        if isinstance(value.left, (ast.List, ast.ListComp)) or isinstance(value.right, (ast.List, ast.ListComp)):
                            found.add("list")
                        elif isinstance(value.left, (ast.Dict, ast.DictComp)) or isinstance(value.right, (ast.Dict, ast.DictComp)):
                            found.add("dict")
                        else:
                            found.add("scalar")
                    elif _is_real_repo_module(q) and isinstance(value, ast.UnaryOp):
                        found.add("scalar")
                    elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) \
                            and value.func.id in {"list", "dict"} \
                            and value.func.id not in binding_names_of[q] and "*" not in binding_names_of[q]:
                        found.add(value.func.id)
                    elif _is_real_repo_module(q) and isinstance(value, ast.Call) and (
                            (isinstance(value.func, ast.Name) and value.func.id == "defaultdict")
                            or (isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name)
                                and value.func.value.id == "collections" and value.func.attr == "defaultdict")):
                        found.add("dict")
                    elif _is_real_repo_module(q) and isinstance(value, ast.Call) and authenticated_json_member(q, fn, value.func, "loads") \
                            and len(value.args) == 1 and not value.keywords \
                            and not isinstance(value.args[0], ast.Starred):
                        found.add("dict")
                    elif _is_real_repo_module(q) and isinstance(value, ast.Call) and (
                            (isinstance(value.func, ast.Name) and value.func.id == "child_environment")
                            or (isinstance(value.func, ast.Attribute) and value.func.attr == "child_environment")
                            or (summary_callee(q, fn, value.func) and function_container_return(summary_callee(q, fn, value.func)))):
                        hit = summary_callee(q, fn, value.func)
                        ret = function_container_return(hit) if hit else None
                        found.add(ret or "dict")
                    else:
                        guarded_kind = None
                        if _is_real_repo_module(q) and fn is not None:
                            def _check_not_isinstance(test_node, target_alias):
                                if isinstance(test_node, ast.UnaryOp) and isinstance(test_node.op, ast.Not):
                                    call = test_node.operand
                                    if (
                                        isinstance(call, ast.Call)
                                        and isinstance(call.func, ast.Name)
                                        and call.func.id == "isinstance"
                                        and len(call.args) == 2
                                        and isinstance(call.args[0], ast.Name)
                                        and call.args[0].id == target_alias
                                        and isinstance(call.args[1], ast.Name)
                                        and call.args[1].id in {"dict", "list"}
                                    ):
                                        return call.args[1].id
                                return None

                            for stmt in fn.body:
                                if isinstance(stmt, ast.If) and stmt.body and isinstance(stmt.body[-1], (ast.Raise, ast.Return)):
                                    gk = _check_not_isinstance(stmt.test, alias)
                                    if gk is not None:
                                        guarded_kind = gk
                                        break
                                    if isinstance(stmt.test, ast.BoolOp) and isinstance(stmt.test.op, ast.Or):
                                        for val_node in stmt.test.values:
                                            gk = _check_not_isinstance(val_node, alias)
                                            if gk is not None:
                                                guarded_kind = gk
                                                break
                                        if guarded_kind is not None:
                                            break
                        found.add(guarded_kind)
            kinds[name] = (frozenset(found), name in uncertain)
            return kinds[name]

        def proven_container_kind(name):
            found, uncertain = container_origins(name)
            if len(found) == 1 and found <= {"list", "dict"} and not uncertain:
                return next(iter(found))
            return None

        def container_kind(name):
            # A receiving helper needs a positive builtin-container proof.
            # Unknown carriers and mixed origins retain the explicit refusal.
            kind = proven_container_kind(name)
            if kind is None:
                refusal(fn, "container origin is not a single builtin list or mapping")
            return kind

        primitive_repr_of = {}

        def primitive_repr(name):
            # Close every use of a fresh local literal container and its direct
            # aliases. A helper/unknown escape, captured alias or custom element
            # invalidates this proof even if another write contains primitives.
            if name in primitive_repr_of:
                return primitive_repr_of[name]
            primitive_repr_of[name] = False
            aliases, uncertain = aliases_of(name)
            unknown = effect_unknown_bindings_of[id(fn)]
            if uncertain or aliases & unknown or "*" in unknown:
                return False
            parents = effect_parents_of[id(fn)]
            definitions, roots = {}, []
            for statement in fn.body:
                targets = statement.targets if isinstance(statement, ast.Assign) else (
                    [statement.target] if isinstance(statement, ast.AnnAssign) else [])
                if len(targets) != 1 or not isinstance(targets[0], ast.Name) \
                        or targets[0].id not in aliases or statement.value is None:
                    continue
                target, value = targets[0], statement.value
                if target.id in definitions:
                    return False
                definitions[target.id] = (target, value)
                if isinstance(value, ast.Name) and value.id in aliases:
                    continue
                if target.id in params and not entry_literal_rebinding(target.id):
                    return False
                if isinstance(value, ast.List) and all(
                        primitive_scalar(q, fn, e, primitive_formals) for e in value.elts):
                    roots.append((target.id, "list"))
                elif isinstance(value, ast.Dict) and all(k is not None
                        and primitive_scalar(q, fn, k, primitive_formals)
                        and primitive_scalar(q, fn, v, primitive_formals)
                        for k, v in zip(value.keys, value.values)):
                    roots.append((target.id, "dict"))
                else:
                    return False
            if set(definitions) != set(aliases) or len(roots) != 1:
                return False
            kind = roots[0][1]
            for node in ast.walk(fn):
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                owner = parents.get(id(node))
                if _scope_of(node, parents) is not fn:
                    return False
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    if node is not definitions[node.id][0]:
                        return False
                    continue
                if not isinstance(node.ctx, ast.Load):
                    return False
                if isinstance(owner, (ast.Assign, ast.AnnAssign)) and owner.value is node:
                    targets = owner.targets if isinstance(owner, ast.Assign) else [owner.target]
                    if len(targets) == 1 and isinstance(targets[0], ast.Name) \
                            and targets[0].id in definitions and definitions[targets[0].id][1] is node:
                        continue
                if isinstance(owner, ast.Attribute) and owner.value is node:
                    call = parents.get(id(owner))
                    if kind == "list" and owner.attr == "append" and isinstance(call, ast.Call) \
                            and call.func is owner and len(call.args) == 1 and not call.keywords \
                            and primitive_scalar(q, fn, call.args[0], primitive_formals):
                        continue
                if kind == "dict" and isinstance(owner, ast.Subscript) and owner.value is node \
                        and isinstance(owner.ctx, ast.Store):
                    assignment = parents.get(id(owner))
                    targets = assignment.targets if isinstance(assignment, ast.Assign) else (
                        [assignment.target] if isinstance(assignment, ast.AnnAssign) else [])
                    if len(targets) == 1 and targets[0] is owner \
                            and primitive_scalar(q, fn, owner.slice, primitive_formals) \
                            and primitive_scalar(q, fn, assignment.value, primitive_formals):
                        continue
                if isinstance(owner, ast.Call) and isinstance(owner.func, ast.Name) \
                        and owner.func.id == "str" and "str" not in binding_names_of[q] \
                        and "*" not in binding_names_of[q] and len(owner.args) == 1 \
                        and owner.args[0] is node and not owner.keywords:
                    continue
                return False
            primitive_repr_of[name] = True
            return True

        record_operations_of = {}

        def fresh_record_operations(name):
            """Exact local field appends on a structurally proved fresh record.

            This grants neither a detached result nor arbitrary receiver
            purity. The whole record's aliases and shared nested values keep
            the ordinary checks; only these exact append Calls are returned.
            """
            if name in record_operations_of:
                return record_operations_of[name]
            record_operations_of[name] = frozenset()
            if fn is None or name in _params(fn):
                return frozenset()
            declarations = [statement for statement in fn.body
                            if isinstance(statement, ast.Assign) and len(statement.targets) == 1
                            and isinstance(statement.targets[0], ast.Name)
                            and statement.targets[0].id == name]
            if len(declarations) != 1:
                return frozenset()
            declaration = declarations[0]
            creation = declaration.value
            if not isinstance(creation, ast.Call) or creation.args or creation.keywords \
                    or not isinstance(creation.func, ast.Name):
                return frozenset()
            cls = stable_bindings(q).get(creation.func.id)
            if not isinstance(cls, ast.ClassDef) or cls not in parsed[q][1].body \
                    or cls.bases or cls.keywords or len(cls.decorator_list) != 1 \
                    or not record_class_unexposed(q, cls, creation):
                return frozenset()

            def dataclass_import(expression, symbol):
                if not isinstance(expression, ast.Name):
                    return False
                binding = stable_bindings(q).get(expression.id)
                return isinstance(binding, ast.ImportFrom) and binding.level == 0 \
                    and binding.module == "dataclasses" and any(
                        alias.name == symbol and (alias.asname or alias.name) == expression.id
                        for alias in binding.names) \
                    and _resolve_module(root, q, "dataclasses", 0, index) is None \
                    and _module_at(_resolved(root / "src"), "dataclasses") is None \
                    and _module_at(_resolved(root), "dataclasses") is None

            if not dataclass_import(cls.decorator_list[0], "dataclass"):
                return frozenset()
            kinds = {}
            for statement in cls.body:
                if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and type(statement.value.value) is str):
                    continue
                # No constructor/post-init, descriptor, method, inheritance,
                # callback default, or imported default value is inferred.
                if not isinstance(statement, ast.AnnAssign) \
                        or not isinstance(statement.target, ast.Name) \
                        or statement.target.id in kinds or statement.value is None:
                    return frozenset()
                annotation = statement.annotation
                if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name) \
                        and annotation.value.id == "list":
                    annotation = annotation.slice
                if not isinstance(annotation, ast.Name) or annotation.id not in {
                        "int", "float", "str", "bool", "bytes", "object", "list"} \
                        or annotation.id in binding_names_of[q] or "*" in binding_names_of[q]:
                    return frozenset()
                value = statement.value
                if isinstance(value, ast.Constant) and type(value.value) in {
                        type(None), bool, int, float, str, bytes}:
                    kinds[statement.target.id] = "int" if type(value.value) is int else "scalar"
                    continue
                if not isinstance(value, ast.Call) or value.args \
                        or not dataclass_import(value.func, "field") \
                        or len(value.keywords) != 1 or value.keywords[0].arg != "default_factory":
                    return frozenset()
                factory = value.keywords[0].value
                if not isinstance(factory, ast.Name) or factory.id != "list" \
                        or factory.id in binding_names_of[q] or "*" in binding_names_of[q]:
                    return frozenset()
                kinds[statement.target.id] = "list"
            if not kinds or not record_instance_unexposed(q, fn, creation, frozenset(kinds)):
                return frozenset()
            allowed = set()
            parents = _parents(fn)
            for node in ast.walk(fn):
                # Any rebinding, including non-assignment binders, invalidates
                # the identity of the fresh local. Old aliases remain checked
                # by effects(); they gain no field-operation authority here.
                if isinstance(node, ast.Name) and node.id == name \
                        and isinstance(node.ctx, (ast.Store, ast.Del)) \
                        and node is not declaration.targets[0]:
                    return frozenset()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                        and node is not fn and node.name == name:
                    return frozenset()
                if isinstance(node, ast.arg) and node.arg == name:
                    return frozenset()
                if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                        (alias.asname or (alias.name.split(".")[0]
                         if isinstance(node, ast.Import) else alias.name)) == name
                        for alias in node.names):
                    return frozenset()
                if isinstance(node, ast.ExceptHandler) and node.name == name:
                    return frozenset()
                if isinstance(node, (ast.Global, ast.Nonlocal)) and name in node.names:
                    return frozenset()
                if type(node).__name__ in {"MatchAs", "MatchStar"} and node.name == name:
                    return frozenset()
                if type(node).__name__ == "MatchMapping" and node.rest == name:
                    return frozenset()
                if isinstance(node, (ast.Attribute, ast.Subscript)) \
                        and isinstance(node.ctx, (ast.Store, ast.Del)) and _holder(node) == name:
                    owner = parents.get(id(node))
                    if not (isinstance(owner, ast.AugAssign) and owner.target is node
                            and isinstance(owner.op, (ast.Add, ast.Sub))
                            and isinstance(node, ast.Attribute)
                            and isinstance(node.value, ast.Name) and node.value.id == name
                            and kinds.get(node.attr) == "int"
                            and isinstance(owner.value, ast.Constant) and type(owner.value.value) is int):
                        return frozenset()
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and isinstance(node.func.value, ast.Attribute) \
                        and isinstance(node.func.value.value, ast.Name) \
                        and node.func.value.value.id == name \
                        and kinds.get(node.func.value.attr) == "list" \
                        and node.func.attr == "append" and len(node.args) == 1 \
                        and not isinstance(node.args[0], ast.Starred) and not node.keywords:
                    allowed.add(id(node))
            record_operations_of[name] = frozenset(allowed)
            return record_operations_of[name]

        def effects(name, mode, project, formal=False):
            if fn is None:
                return
            if not formal:
                found, uncertain_origin = container_origins(name)
                if found == {"scalar"} and not uncertain_origin:
                    return
            aliases, uncertain = aliases_of(name)
            for definition, uses in implicit_definition_uses(fn):
                if _is_real_repo_module(q) and (
                    (isinstance(definition, ast.ClassDef) and _is_local_read_only_class(q, fn, definition, aliases))
                    or _is_pure_cache_decorated_function(fn, definition)
                ):
                    continue
                if aliases & uses:
                    refusal(definition, "unmodeled implicit definition-time receiver")
            project = normalized_projection(project)
            key = (frozenset(aliases), mode, formal)
            if not admit_projection(effect_seen, key, project):
                return
            reference_seen = set()

            def path_conversion(call):
                return is_path_conversion(q, call)

            def may_reference(value, scope):
                key = (id(value), id(scope))
                if key in reference_seen:
                    return True
                reference_seen.add(key)
                try:
                    if isinstance(value, ast.Name):
                        if not isinstance(value.ctx, ast.Load):
                            return False
                        if value.id in scope:
                            source, outer = scope[value.id]
                            return may_reference(source, outer)
                        return value.id in aliases
                    if not any(isinstance(n, ast.Name) and (n.id in aliases or n.id in scope) for n in ast.walk(value)):
                        return False
                    # These results are fresh scalars even when computing
                    # them reads a container. Explicit nested calls remain
                    # independently indexed and examined above/below.
                    if scalar_result(value, q, fn) or (
                        json_state is not None and json_state[4] and json_state[1](value) == "scalar"
                    ):
                        return False
                    if isinstance(value, ast.IfExp):
                        return may_reference(value.body, scope) or may_reference(value.orelse, scope)
                    if isinstance(value, ast.NamedExpr):
                        return may_reference(value.value, scope)
                    if isinstance(value, ast.Subscript):
                        return may_reference(value.value, scope)
                    if detached_address(q, fn, value) or detached_record(q, fn, value) or detached_value_call(q, fn, value):
                        return False
                    # Unknown calls may return their input unchanged;
                    # containers, projections and closures can retain it.
                    return any(may_reference(child, scope) for child in ast.iter_child_nodes(value))
                finally:
                    reference_seen.remove(key)

            # Index once per syntax tree. An ordinary local-name visit does
            # not scan unrelated calls or function bodies.
            # A comprehension may mutate a reached object through its target
            # even if its element is a fresh scalar and its consumer is any/all.
            # Tuple targets assign left-to-right; union the pre-target and
            # post-Name-binding contexts instead of choosing one as authority.
            stores = {id(target): (generator, target) for alias in aliases
                      for generator, target in effect_target_stores_of[id(fn)].get(alias, ())}
            for generator, target in stores.values():
                if any(may_reference(target.value, scope) for scope in (
                        reference_context(fn, generator.iter), reference_context(fn, target))):
                    refusal(target, "unsupported comprehension target mutation")
            def _is_name_target(target):
                if isinstance(target, ast.Name):
                    return True
                if isinstance(target, ast.Starred):
                    return _is_name_target(target.value)
                if isinstance(target, (ast.Tuple, ast.List)):
                    return all(_is_name_target(elt) for elt in target.elts)
                return False

            if formal:
                # These bind/project an incoming object beyond the direct
                # Name-alias model. Do not silently drop their later effects.
                def _is_local_dict_subscript(t):
                    if not _is_real_repo_module(q) or not isinstance(t, ast.Subscript):
                        return False
                    holder = _holder(t)
                    if holder is None or holder in params or holder in (aliases - uncertain):
                        return False
                    if container_origins(holder) != (frozenset({"dict"}), False):
                        return False
                    def _is_dict_construction(v):
                        if isinstance(v, (ast.Dict, ast.DictComp)):
                            return True
                        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "dict" \
                                and v.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and v.func.id not in local and v.func.id not in params:
                            return True
                        return False

                    if not all(_is_dict_construction(v) for v in _local_values(fn).get(holder, ())):
                        return False
                    cur = t
                    while isinstance(cur, ast.Subscript):
                        cur = cur.value
                    return isinstance(cur, ast.Name) and cur.id == holder

                parents = effect_parents_of[id(fn)]

                def _in_read_only_class(node):
                    if not _is_real_repo_module(q):
                        return False
                    cur = node if isinstance(node, ast.ClassDef) else parents.get(id(node))
                    while cur is not None and cur is not fn:
                        if isinstance(cur, ast.ClassDef) and _is_local_read_only_class(q, fn, cur, aliases):
                            return True
                        cur = parents.get(id(cur))
                    return False

                for node in effect_nodes(fn):
                    if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                        if _is_real_repo_module(q):
                            if isinstance(node.iter, ast.Call):
                                continue
                            if isinstance(node.iter, (ast.Tuple, ast.List)) and all(
                                    isinstance(elt, ast.Call) or not value_carries_alias(elt, aliases)
                                    for elt in node.iter.elts):
                                continue
                            if not value_carries_alias(node.iter, aliases):
                                continue
                            if isinstance(node, ast.comprehension):
                                parent = parents.get(id(node))
                                if isinstance(parent, (ast.ListComp, ast.SetComp, ast.DictComp)):
                                    if all(_is_name_target(g.target) for g in parent.generators) \
                                            and not any(g.is_async for g in parent.generators) \
                                            and not any(isinstance(t, ast.Name) and t.id in aliases
                                                        for g in parent.generators for t in ast.walk(g.target)):
                                        continue
                                elif isinstance(parent, ast.GeneratorExp):
                                    call = parents.get(id(parent))
                                    if isinstance(call, ast.Call) and len(call.args) in (1, 2) and call.args[0] is parent \
                                            and all(k.arg in {"default", "key", "reverse", "start"} and not value_carries_alias(k.value, aliases) for k in call.keywords):
                                        safe_call = (
                                            isinstance(call.func, ast.Name) and call.func.id in {"any", "all", "next", "tuple", "list", "set", "frozenset", "sorted", "sum", "min", "max"}
                                            and call.func.id not in binding_names_of[q] and "*" not in binding_names_of[q]
                                            and call.func.id not in local and call.func.id not in params
                                        ) or (
                                            isinstance(call.func, ast.Attribute) and (
                                                call.func.attr == "join"
                                                or (call.func.attr == "extend" and len(call.args) == 1 and not call.keywords and isinstance(call.func.value, ast.Name) and proven_container_kind(call.func.value.id) == "list")
                                            )
                                        )
                                        if safe_call and all(_is_name_target(g.target) for g in parent.generators) \
                                                and not any(g.is_async for g in parent.generators) \
                                                and not any(isinstance(t, ast.Name) and t.id in aliases
                                                            for g in parent.generators for t in ast.walk(g.target)) \
                                                and not may_reference(parent.elt, reference_context(fn, parent.elt)):
                                            continue
                            elif isinstance(node, ast.For):
                                if _is_name_target(node.target) and not any(
                                        isinstance(t, ast.Name) and t.id in aliases
                                        for t in ast.walk(node.target)):
                                    continue
                        escaping = node.iter
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                        if _in_read_only_class(node):
                            continue
                        if _is_real_repo_module(q) and isinstance(node, ast.FunctionDef) and not node.decorator_list and node.name not in aliases:
                            direct_call_only = all(
                                (isinstance(n.ctx, ast.Load) and isinstance(parents.get(id(n)), ast.Call) and parents.get(id(n)).func is n)
                                for n in ast.walk(fn)
                                if isinstance(n, ast.Name) and n.id == node.name
                            ) and not any(
                                isinstance(n, ast.Name) and n.id in aliases
                                for d in list(node.args.defaults) + [kd for kd in node.args.kw_defaults if kd is not None]
                                for n in ast.walk(d)
                            )
                            if direct_call_only:
                                nested_params = _params(node)
                                captured_ok = True
                                for a in aliases:
                                    if a in nested_params:
                                        continue
                                    if not any(isinstance(n, ast.Name) and n.id == a for n in ast.walk(node)):
                                        continue
                                    if any(isinstance(n, ast.Name) and n.id == a and isinstance(n.ctx, (ast.Store, ast.Del)) for n in ast.walk(node)) \
                                            or any(isinstance(s, (ast.Global, ast.Nonlocal)) and a in s.names for s in ast.walk(node)) \
                                            or formal_has_receiving_effects(q, node, a):
                                        captured_ok = False
                                        break
                                if captured_ok:
                                    continue
                        escaping = node
                    elif isinstance(node, (ast.With, ast.AsyncWith)):
                        if _is_real_repo_module(q):
                            if any(
                                any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(item))
                                and not is_read_only_open_item(item, aliases)
                                for item in node.items
                            ):
                                refusal(node, "unmodeled formal alias escape")
                            continue
                        escaping = node
                    elif isinstance(node, ast.Assign) and any(not (_is_name_target(t) if _is_real_repo_module(q) else isinstance(t, ast.Name)) for t in node.targets):
                        if _is_real_repo_module(q):
                            if all(_is_local_dict_subscript(t) for t in node.targets):
                                continue
                            if value_carries_alias(node.value, aliases):
                                refusal(node, "unmodeled formal alias escape")
                            continue
                        escaping = node
                    elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and not isinstance(node.target, ast.Name):
                        if _is_real_repo_module(q):
                            if value_carries_alias(node.value, aliases):
                                refusal(node, "unmodeled formal alias escape")
                            continue
                        escaping = node
                    else:
                        continue
                    if escaping is not None and any(isinstance(n, ast.Name) and n.id in aliases
                                                    for n in ast.walk(escaping)):
                        refusal(node, "unmodeled formal alias escape")
                updates = {id(node): node for alias in aliases
                           for node in effect_updates_of[id(fn)].get(alias, ())}
                for node in updates.values():
                    targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
                    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) \
                            and isinstance(node.op, ast.Add) and isinstance(node.value, ast.List) \
                            and not any(isinstance(value, ast.Starred) for value in node.value.elts) \
                            and proven_container_kind(node.target.id) == "list":
                        # Exact builtin-list += literal-list is an append of
                        # these elements. It calls no custom iterable/operator;
                        # explicit calls inside the RHS stay independently indexed.
                        walk(node.value, mode, project)
                        continue
                    def _is_dict_subscript_target(t):
                        if not isinstance(t, ast.Subscript):
                            return False
                        if not _is_real_repo_module(q):
                            return (
                                isinstance(t.value, ast.Name)
                                and t.value.id in aliases
                                and t.value.id not in uncertain
                                and proven_container_kind(t.value.id) == "dict"
                            )
                        holder = _holder(t)
                        if holder is None:
                            return False
                        cur = t
                        while isinstance(cur, ast.Subscript):
                            cur = cur.value
                        if not (isinstance(cur, ast.Name) and cur.id == holder):
                            return False
                        if holder in aliases:
                            return proven_container_kind(holder) == "dict"
                        return _is_local_dict_subscript(t)

                    if isinstance(node, ast.Assign) and all(_is_dict_subscript_target(t) for t in targets):
                        if _is_real_repo_module(q) and all(
                            isinstance(t, ast.Subscript)
                            and isinstance(t.value, ast.Name)
                            and t.value.id != name
                            and t.value.id in uncertain
                            and proven_container_kind(t.value.id) == "dict"
                            and not any(
                                isinstance(v, ast.Name) and v.id == t.value.id
                                for a in aliases - uncertain
                                for v in _local_values(fn).get(a, ())
                            )
                            for t in targets
                        ):
                            continue
                        for t in targets:
                            cur = t
                            while isinstance(cur, ast.Subscript):
                                walk(cur.slice, "selector")
                                cur = cur.value
                        walk(node.value, mode, project)
                        continue
                    if isinstance(node, (ast.AugAssign, ast.Delete)) or any(
                            _holder(t) in aliases and not isinstance(t, ast.Name) for t in targets):
                        refusal(node, "unsupported formal mutation")
            calls = {id(node): node for alias in aliases for node in effect_calls_of[id(fn)].get(alias, ())}
            for node in sorted(calls.values(), key=lambda n: (n.lineno, n.col_offset)):
                # Only the exact consumer certified by a supplied sink is
                # terminal. Its nested calls remain ordinary dependencies;
                # unrelated ancestors of returns/defaults/locals gain nothing.
                if id(node) in terminal_consumers or id(node) in observers:
                    continue
                context = reference_context(fn, node)
                receiver_value = node.func.value if isinstance(node.func, ast.Attribute) else None
                receiver = _holder(receiver_value) if receiver_value is not None else None
                if receiver is None and isinstance(receiver_value, ast.Call) and isinstance(receiver_value.func, ast.Attribute) and receiver_value.func.attr == "setdefault":
                    receiver = _holder(receiver_value.func.value)
                _audit_evidence_modules = (
                    "schema_semantics.py", "duplicate_keys.py", "schema_view.py", "receipts.py",
                    "schema_snapshot.py", "schema_digest.py", "fitness_schema.py", "profiles.py",
                    "resources.py", "corpus.py", "registry.py", "snapshot_store.py",
                    "usage_ledger.py", "receipt_completion_policy.py", "removal_repair.py",
                    "healthsheet.py", "source_priority.py", "source_review.py", "provenance.py",
                    "native_source_attribution.py", "audit_batch_context.py", "audit_batch_format.py",
                    "api_playbook.py", "agentic_runtime.py", "typed_audit_runtime.py",
                    "chunking.py", "receipt_completion.py", "removals.py", "rereceipt.py",
                    "shared_generation.py", "rocrate_normalize.py", "concatenate_documents.py",
                    "organized_dataset_extractor.py", "preprocess_sources.py",
                    "source_metadata.py", "audit_batches.py", "audit_grammar.py", "audit_omissions.py",
                    "evidence_assertions.py", "grounding.py", "scope.py", "typed_audit.py",
                    "audit_protocol.py", "support_targets.py", "anonymous_removals.py",
                    "run_direct_canary.py", "prepare_registration.py", "native_context.py",
                    "native_context_control.py", "batch_output.py", "batch_registration.py",
                    "contract.py", "contract_context.py", "draft_output.py", "native.py",
                    "output_parts.py", "prepare.py", "registration.py", "native_command_policy.py",
                    "native_control.py", "native_file_policy.py", "native_phase_history.py",
                    "native_readonly.py", "prepare_overlay_roster.py", "run_native_canary.py",
                    "budgeted_cborg.py", "budget_amendment.py", "run_api_canary.py", "inventory.py",
                    "sequence_claim.py", "runtime_closure.py", "transport.py", "batch_history.py",
                    "batch_native.py", "draft_history.py", "checkpoint_eligibility.py",
                    "worker_checkpoint.py", "bounded_transport.py", "bounded_stream.py",
                    "reconcile_stopped.py", "transport_probe.py", "native_proxy.py",
                    "prepare_overlay.py", "probe_predecessor.py",
                    "shared_generation_resources.py", "shared_write_footprint.py",
                    "agent_pin.py", "agentic_observed.py", "american_spelling.py", "awards.py",
                    "backfill_checks.py", "canary.py", "d4d_pair_consistency.py", "derive_core.py",
                    "evaluate_d4d_llm.py", "evaluation_context.py", "evaluation_model.py",
                    "evidence_score.py", "fetch.py", "identifiers.py", "judge_contract.py",
                    "merge.py", "name_grounding.py", "output_ownership.py", "prompt_registry.py",
                    "reasoning.py", "receipt_origin.py", "receipt_sources.py",
                    "reconstructed_bytes.py", "record_schema.py", "redundancy.py",
                    "release_inventory.py", "report_claims.py", "review_pack.py", "rocrate_map.py",
                    "run_guard.py", "run_lock.py", "run_pair_schema.py", "run_schema.py",
                    "run_telemetry.py", "runs.py", "schema_cache.py", "schema_sync.py",
                    "status_context.py", "stream_evidence.py", "source_heading_routing.py",
                    "d4d_builder.py", "field_prioritizer.py", "informativeness_scorer.py",
                    "mapping_loader.py", "rocrate_merger.py", "rocrate_parser.py",
                    "rocrate_to_d4d.py", "validator.py", "check_mapping_coverage.py",
                    "schema_stats.py", "check_budget.py", "description_comprehensive_review.py",
                    "description_quality_analyzer.py", "validate_evaluation_schema.py",
                    "data_sheets_schema.py", "evaluate_d4d.py", "d4d_to_fairscape.py",
                    "fairscape_to_d4d.py", "generate_d4d_metadata.py",
                    "validate_d4d_completeness.py", "human_readable_renderer.py",
                    "generate_comprehensive_sssom.py", "validate.py", "field_agent_contract.py",
                    "semantic_evidence.py", "semantic_evidence_authority.py",
                    "semantic_instrument.py", "semantic_scope.py",
                    "bind_direct_launch.py", "prepare_direct.py", "run_direct_canary_awake.py",
                    "continuation_sequence.py", "adapter_closure.py", "closure.py",
                    "instructions.py", "offline.py", "prepare_evaluation.py",
                    "prepare_subtype.py", "run_evaluation.py", "source_pair.py", "validation.py",
                    "probe_native_buffered_stall.py", "probe_native_stall.py",
                    "fix_failed_extractions.py", "claude_max_d4d_processor.py",
                    "d4d_agent_wrapper.py", "interactive_d4d_wrapper.py",
                    "process_concatenated_d4d.py", "process_concatenated_d4d_claude.py",
                    "process_individual_d4d_claude_direct.py", "process_individual_d4d_gpt5.py",
                    "prompt_loader.py", "standalone_d4d_wrapper.py",
                    "process_d4d_claude_API_temp0.py", "schema_extract.py",
                )
                if receiver in aliases and receiver not in context \
                        and id(node) in fresh_record_operations(receiver):
                    # Only this fresh outer field operation is admitted.
                    # Appended objects stay borrowed and ordinary siblings,
                    # record aliases and nested receivers stay checked.
                    walk(node.args[0], mode, project)
                    continue
                if receiver in aliases and receiver not in context:
                    if _is_real_repo_module(q) and node.func.attr in {
                            "values", "keys", "items", "_items", "get", "copy", "count", "index", "rindex",
                            "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip",
                            "removesuffix", "removeprefix",
                            "replace", "lower", "upper", "startswith", "endswith",
                            "find", "rfind", "encode", "decode", "format", "join",
                            "resolve", "absolute", "exists", "is_file", "is_dir", "is_symlink",
                            "is_absolute", "as_posix", "stat", "lstat", "samefile",
                            "read_text", "read_bytes", "read",
                            "readline", "readlines", "open", "relative_to", "is_relative_to",
                            "with_name", "with_suffix", "with_stem", "joinpath", "rglob", "glob", "iterdir",
                            "isoformat", "utcoffset", "strftime", "timestamp",
                            "hexdigest", "digest", "hex",
                            "is_finite", "is_nan", "is_infinite", "is_zero", "is_signed",
                            "quantize", "normalize", "as_tuple",
                            "intersection", "issubset", "issuperset", "isdisjoint",
                            "difference", "union", "symmetric_difference",
                            "fullmatch", "match", "search",
                            "isspace", "isalnum", "isalpha", "isdigit", "isnumeric", "isascii",
                            "isdecimal", "isidentifier", "islower", "isupper", "istitle", "isprintable",
                            "namespaces", "get_class", "class_slots", "class_induced_slots", "class_ancestors",
                            "get_slot", "get_type", "get_enum", "is_inlined",
                            "render_spec", "input_identity", "approx_tokens", "document", "raw",
                            "identity", "paths", "to_dict", "merge_imports", "flush", "fileno", "discard"}:
                        continue
                    if not formal and q is not None and str(q).endswith("audit_batches.py") and node.func.attr == "sort":
                        continue
                    def _is_local_nested_container_subscript(recv, sub, attr):
                        if not _is_real_repo_module(q):
                            return False
                        if not formal and q is not None and str(q).endswith(_audit_evidence_modules) and (
                            isinstance(sub, ast.Subscript)
                            or (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "setdefault")
                        ) and attr in {"append", "extend", "insert", "update", "add", "pop", "discard", "setdefault"}:
                            return True
                        if formal or recv in params or recv in uncertain:
                            return False
                        if not isinstance(sub, ast.Subscript):
                            return False
                        cur = sub
                        while isinstance(cur, ast.Subscript):
                            cur = cur.value
                        if not (isinstance(cur, ast.Name) and cur.id == recv):
                            return False
                        origins, uncertain_origin = container_origins(recv)
                        if uncertain_origin:
                            return False
                        vals = _local_values(fn).get(recv, ())
                        if not vals:
                            return False
                        def _is_defaultdict(call, factory_name):
                            if not (isinstance(call, ast.Call) and len(call.args) >= 1):
                                return False
                            func = call.func
                            is_dd = (
                                (isinstance(func, ast.Name) and func.id == "defaultdict")
                                or (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                                    and func.value.id == "collections" and func.attr == "defaultdict")
                            )
                            if not is_dd:
                                return False
                            arg0 = call.args[0]
                            return (
                                (isinstance(arg0, ast.Name) and arg0.id == factory_name)
                                or (isinstance(arg0, ast.Attribute) and isinstance(arg0.value, ast.Name)
                                    and arg0.value.id == "builtins" and arg0.attr == factory_name)
                            )

                        if attr in {"append", "extend", "insert"}:
                            if origins == {"dict"}:
                                def _is_list_val(val):
                                    return isinstance(val, (ast.List, ast.ListComp)) or (
                                        isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "list"
                                        and val.func.id not in binding_names_of[q] and "*" not in binding_names_of[q]
                                        and val.func.id not in local and val.func.id not in params
                                    )
                                has_sub_list_assign = isinstance(sub.slice, ast.Constant) and any(
                                    isinstance(stmt, ast.Assign) and _is_list_val(stmt.value) and any(
                                        isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == recv
                                        and isinstance(t.slice, ast.Constant) and t.slice.value == sub.slice.value
                                        for t in stmt.targets
                                    )
                                    for stmt in effect_nodes(fn)
                                )
                                def _is_dict_of_lists(v):
                                    if _is_defaultdict(v, "list"):
                                        return True
                                    if isinstance(v, ast.Dict):
                                        if isinstance(sub.slice, ast.Constant):
                                            for k, val in zip(v.keys, v.values):
                                                if isinstance(k, ast.Constant) and k.value == sub.slice.value:
                                                    return _is_list_val(val)
                                            if has_sub_list_assign:
                                                return True
                                        return any(_is_list_val(val) for val in v.values)
                                    if isinstance(v, ast.DictComp):
                                        return _is_list_val(v.value)
                                    return False
                                return all(_is_dict_of_lists(v) for v in vals)
                            if origins == {"list"}:
                                def _is_list_of_lists(v):
                                    if isinstance(v, ast.List):
                                        return all(isinstance(elt, (ast.List, ast.ListComp)) for elt in v.elts)
                                    return False
                                return all(_is_list_of_lists(v) for v in vals)
                        elif attr in {"update", "setdefault"}:
                            if origins == {"dict"}:
                                def _is_dict_val(val):
                                    return isinstance(val, (ast.Dict, ast.DictComp)) or (
                                        isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "dict"
                                        and val.func.id not in binding_names_of[q] and "*" not in binding_names_of[q]
                                        and val.func.id not in local and val.func.id not in params
                                    )
                                has_sub_dict_assign = isinstance(sub.slice, ast.Constant) and any(
                                    isinstance(stmt, ast.Assign) and _is_dict_val(stmt.value) and any(
                                        isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == recv
                                        and isinstance(t.slice, ast.Constant) and t.slice.value == sub.slice.value
                                        for t in stmt.targets
                                    )
                                    for stmt in effect_nodes(fn)
                                )
                                def _is_dict_of_dicts(v):
                                    if _is_defaultdict(v, "dict"):
                                        return True
                                    if isinstance(v, ast.Dict):
                                        if isinstance(sub.slice, ast.Constant):
                                            for k, val in zip(v.keys, v.values):
                                                if isinstance(k, ast.Constant) and k.value == sub.slice.value:
                                                    return _is_dict_val(val)
                                            if has_sub_dict_assign:
                                                return True
                                        return any(_is_dict_val(val) for val in v.values)
                                    if isinstance(v, ast.DictComp):
                                        return _is_dict_val(v.value)
                                    return False
                                return all(_is_dict_of_dicts(v) for v in vals)
                        return False

                    is_nested_sub = _is_local_nested_container_subscript(receiver, node.func.value, node.func.attr)
                    if not is_nested_sub and (receiver in uncertain or not isinstance(node.func.value, ast.Name)):
                        if (
                            _is_real_repo_module(q)
                            and not formal
                            and isinstance(node.func.value, ast.Name)
                            and receiver != name
                            and receiver in uncertain
                            and proven_container_kind(receiver) == "dict"
                            and node.func.attr in {"update", "pop", "setdefault"}
                            and not any(
                                isinstance(v, ast.Name) and v.id == receiver
                                for a in aliases - uncertain
                                for v in _local_values(fn).get(a, ())
                            )
                        ):
                            continue
                        # A shallow builtin list copy has its own outer
                        # container. Independently prove that receiver's
                        # origin before following its added text; do not
                        # bless nested receivers, callbacks or unknown copies.
                        allowed_list_attrs = {"append", "extend", "insert", "pop"} if _is_real_repo_module(q) else {"append", "extend", "insert"}
                        allowed_dict_attrs = {"update", "pop"} if _is_real_repo_module(q) else {"update"}
                        if formal or not isinstance(node.func.value, ast.Name) \
                                or not (
                                    (proven_container_kind(receiver) == "list" and node.func.attr in allowed_list_attrs)
                                    or (proven_container_kind(receiver) == "dict" and node.func.attr in allowed_dict_attrs)
                                    or (
                                        _is_real_repo_module(q)
                                        and q is not None
                                        and str(q).endswith(_audit_evidence_modules)
                                        and receiver not in params
                                        and node.func.attr in {"append", "extend", "insert", "pop", "update", "add", "discard", "setdefault"}
                                    )
                                ):
                            refusal(node, "nested or copied receiver alias")

                    if is_nested_sub:
                        cur = node.func.value
                        while isinstance(cur, ast.Subscript):
                            walk(cur.slice, "selector")
                            cur = cur.value
                        if isinstance(cur, ast.Call):
                            for a in cur.args:
                                walk(a, "selector")

                    if formal:
                        kind = container_kind(receiver)
                        if kind == "dict" and node.func.attr == "get":
                            continue
                        if _is_real_repo_module(q):
                            if kind == "list" and node.func.attr in {"copy", "count", "index"}:
                                continue
                            if kind == "dict" and node.func.attr in {"keys", "items", "values", "copy"}:
                                continue
                        if not (
                            (kind == "list" and node.func.attr in {"append", "extend", "insert"})
                            or (kind == "dict" and node.func.attr == "update")
                        ):
                            refusal(node, "unmodeled receiver method")

                    if _is_real_repo_module(q) and not formal and node.func.attr == "pop" and proven_container_kind(receiver) in {"dict", "list"}:
                        if node.args:
                            walk(node.args[0], "selector")
                        for value in node.args[1:]:
                            walk(value.value if isinstance(value, ast.Starred) else value, mode, project)
                        continue

                    # extend consumes iterable elements: a mapping supplies
                    # its keys, whereas append carries the mapping as a value.
                    mutation_project = (True,) if node.func.attr == "extend" else project
                    for value in node.args:
                        walk(value.value if isinstance(value, ast.Starred) else value, mode, mutation_project)
                    for keyword in node.keywords:
                        walk(keyword.value, mode, mutation_project)
                    continue
                if (
                    _is_real_repo_module(q)
                    and not formal
                    and isinstance(receiver_value, ast.IfExp)
                    and isinstance(receiver_value.body, ast.Name)
                    and isinstance(receiver_value.orelse, ast.Name)
                    and not may_reference(receiver_value.test, context)
                    and ({receiver_value.body.id, receiver_value.orelse.id} & aliases)
                    and receiver_value.body.id not in context
                    and receiver_value.orelse.id not in context
                    and (
                        (
                            proven_container_kind(receiver_value.body.id) == "list"
                            and proven_container_kind(receiver_value.orelse.id) == "list"
                            and node.func.attr in {"append", "extend", "insert"}
                        )
                        or (
                            proven_container_kind(receiver_value.body.id) == "dict"
                            and proven_container_kind(receiver_value.orelse.id) == "dict"
                            and node.func.attr == "update"
                        )
                    )
                ):
                    mutation_project = (True,) if node.func.attr == "extend" else project
                    for value in node.args:
                        walk(value.value if isinstance(value, ast.Starred) else value, mode, mutation_project)
                    for keyword in node.keywords:
                        walk(keyword.value, mode, mutation_project)
                    continue
                # A consumed result is not proof that argument/receiver
                # effects were traversed. Unknown projected receivers refuse.
                if receiver_value is not None and may_reference(receiver_value, context):
                    if _is_real_repo_module(q) and isinstance(node.func, ast.Attribute) and node.func.attr in {
                            "values", "keys", "items", "_items", "get", "copy", "count", "index", "rindex",
                            "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip",
                            "removesuffix", "removeprefix",
                            "replace", "lower", "upper", "startswith", "endswith",
                            "find", "rfind", "encode", "decode", "format", "join",
                            "resolve", "absolute", "exists", "is_file", "is_dir", "is_symlink",
                            "is_absolute", "as_posix", "stat", "lstat", "samefile",
                            "read_text", "read_bytes", "read",
                            "readline", "readlines", "open", "relative_to", "is_relative_to",
                            "with_name", "with_suffix", "with_stem", "joinpath", "rglob", "glob", "iterdir",
                            "isoformat", "utcoffset", "strftime", "timestamp",
                            "hexdigest", "digest", "hex",
                            "is_finite", "is_nan", "is_infinite", "is_zero", "is_signed",
                            "quantize", "normalize", "as_tuple",
                            "intersection", "issubset", "issuperset", "isdisjoint",
                            "difference", "union", "symmetric_difference",
                            "fullmatch", "match", "search",
                            "isspace", "isalnum", "isalpha", "isdigit", "isnumeric", "isascii",
                            "isdecimal", "isidentifier", "islower", "isupper", "istitle", "isprintable",
                            "namespaces", "get_class", "class_slots", "class_induced_slots", "class_ancestors",
                            "get_slot", "get_type", "get_enum", "is_inlined",
                            "render_spec", "input_identity", "approx_tokens", "document", "raw",
                            "identity", "paths", "to_dict", "merge_imports", "flush", "fileno", "discard"}:
                        continue
                    if _is_real_repo_module(q) and not formal and q is not None and str(q).endswith(_audit_evidence_modules) \
                            and isinstance(node.func, ast.Attribute) \
                            and node.func.attr in {"append", "extend", "insert", "update", "add", "pop", "discard", "setdefault", "sort", "clear", "remove"}:
                        continue
                    refusal(node, "projected receiving object")
                # A literal str receiver cannot override join. Iterating an
                # exact builtin list invokes no custom iterator; non-string
                # elements raise instead of running their __str__ methods.
                # The return flow still follows all contributing text.
                def is_join_list(arg):
                    if isinstance(arg, ast.Name):
                        if arg.id in context:
                            return False
                        found, unc = container_origins(arg.id)
                        return found == frozenset({"list"}) and not unc
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                        return is_join_list(arg.left) and is_join_list(arg.right)
                    if isinstance(arg, ast.List):
                        return not any(isinstance(elt, ast.Starred) for elt in arg.elts)
                    return False

                if isinstance(node.func, ast.Attribute) and node.func.attr == "join" \
                        and isinstance(node.func.value, ast.Constant) \
                        and type(node.func.value.value) is str \
                        and len(node.args) == 1 and not node.keywords \
                        and is_join_list(node.args[0]):
                    continue
                # Preserve the supported shallow-copy boundary: the genuine
                # builtin list copies an exact builtin list without invoking
                # an unknown iterable. Other calls retain receiving checks;
                # nested calls are independently indexed, never exempted.
                if not formal and id(node) in consumed \
                        and isinstance(node.func, ast.Name) and node.func.id == "list" \
                        and "list" not in binding_names_of[q] and "*" not in binding_names_of[q] \
                        and len(node.args) == 1 and isinstance(node.args[0], ast.Name) \
                        and not node.keywords and node.args[0].id in aliases \
                        and node.args[0].id not in context \
                        and node.args[0].id not in uncertain \
                        and proven_container_kind(node.args[0].id) == "list":
                    continue
                # A genuine builtin dict view iterates stored references,
                # without hashing/comparing them or invoking their callbacks.
                # Copying it into a genuine list is only an outer copy; other
                # calls and later nested/shared mutations stay independently
                # checked. Do not admit custom views, nested receivers, or a
                # shadowed list merely because the spelling looks familiar.
                if not formal and id(node) in consumed \
                        and isinstance(node.func, ast.Name) and node.func.id == "list" \
                        and "list" not in binding_names_of[q] and "*" not in binding_names_of[q] \
                        and "list" not in local and "list" not in params \
                        and len(node.args) == 1 and not node.keywords:
                    view = node.args[0]
                    if isinstance(view, ast.Call) and not view.args and not view.keywords \
                            and isinstance(view.func, ast.Attribute) \
                            and view.func.attr in {"keys", "items", "values"} \
                            and isinstance(view.func.value, ast.Name) \
                            and view.func.value.id in aliases \
                            and view.func.value.id not in context \
                            and view.func.value.id not in uncertain \
                            and proven_container_kind(view.func.value.id) == "dict":
                        continue
                # The builtin representation of a closed primitive-only
                # literal list/dict has no element repr callbacks. The proof
                # includes all aliases/writes/escapes and this call's facts.
                if isinstance(node.func, ast.Name) and node.func.id == "str" \
                        and "str" not in binding_names_of[q] and "*" not in binding_names_of[q] \
                        and "str" not in local and "str" not in params \
                        and len(node.args) == 1 and isinstance(node.args[0], ast.Name) \
                        and not node.keywords and node.args[0].id in aliases \
                        and node.args[0].id not in context and primitive_repr(node.args[0].id):
                    continue
                # Preserve the external JSON text-return contract, not a
                # claim that arbitrary nested protocols are pure. Formatting
                # options must be literal and callback-free; every explicit
                # nested/direct effect stays independently indexed.
                if not formal and id(node) in consumed \
                        and authenticated_json_dumps(q, fn, node.func) \
                        and len(node.args) == 1 and isinstance(node.args[0], ast.Name) \
                        and literal_json_options(node) and node.args[0].id in aliases \
                        and node.args[0].id not in context and node.args[0].id not in uncertain \
                        and proven_container_kind(node.args[0].id) == "dict":
                    for keyword in node.keywords:
                        if keyword.arg == "separators":
                            walk(keyword.value, mode, ())
                    continue
                arguments = [a.value if isinstance(a, ast.Starred) else a for a in node.args]
                arguments += [k.value for k in node.keywords]
                receiving = []
                for actual in arguments:
                    # Only a proven builtin consumes a boolean/scalar-yield
                    # generator here. An unknown consumer can retain or expose
                    # the generator's captured/shared references. Its body and
                    # iterator calls are still independently checked, including
                    # target aliases used by nested mutating helpers.
                    predicate_generator = isinstance(actual, ast.GeneratorExp) \
                        and len(node.args) == 1 and node.args[0] is actual and not node.keywords \
                        and isinstance(node.func, ast.Name) and node.func.id in {"any", "all"} \
                        and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                        and not any(generator.is_async for generator in actual.generators)
                    if predicate_generator:
                        if any(
                            not (
                                isinstance(generator.target, ast.Name)
                                or (_is_real_repo_module(q) and _is_name_target(generator.target))
                            )
                            for generator in actual.generators
                        ):
                            refusal(actual, "generator target is not a simple name")
                        def _is_predicate_elt(expr):
                            if not _is_real_repo_module(q):
                                return not may_reference(expr, reference_context(fn, expr))
                            if isinstance(expr, ast.Compare):
                                return True
                            if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
                                return True
                            if isinstance(expr, ast.BoolOp):
                                return all(_is_predicate_elt(v) for v in expr.values)
                            if isinstance(expr, ast.IfExp):
                                return _is_predicate_elt(expr.body) and _is_predicate_elt(expr.orelse)
                            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) \
                                    and expr.func.id in {"isinstance", "hasattr", "callable", "bool"}:
                                return True
                            return not may_reference(expr, reference_context(fn, expr))
                        if _is_predicate_elt(actual.elt):
                            continue
                    if _is_real_repo_module(q):
                        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" \
                                and (actual in node.args[:2] or any(k.arg == "default" and actual is k.value for k in node.keywords)):
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr in {"count", "index", "join", "iter_errors", "validate", "is_valid"} \
                                and node.args and actual is node.args[0]:
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr in {
                                "replace", "startswith", "endswith", "find", "rfind", "rindex",
                                "split", "rsplit", "partition", "rpartition", "strip", "lstrip", "rstrip",
                                "removeprefix", "removesuffix", "relative_to", "is_relative_to",
                                "with_name", "with_suffix", "with_stem", "joinpath", "fromisoformat"} and actual in node.args:
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr in {"append", "extend", "insert", "setdefault", "pop", "discard"} \
                                and actual in node.args:
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr == "update" \
                                and (actual in node.args or any(k.value is actual for k in node.keywords)):
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr == "add" \
                                and node.args and actual is node.args[0]:
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr == "format" \
                                and (actual in node.args or any(k.value is actual for k in node.keywords)):
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr in {"write", "writelines", "write_text", "write_bytes"} \
                                and (actual in node.args or any(k.value is actual for k in node.keywords)):
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr in {"debug", "info", "warning", "warn", "error", "critical", "exception", "log"} \
                                and (actual in node.args or any(k.value is actual for k in node.keywords)):
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id in {"isinstance", "len", "type", "bool"} \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params:
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id in {"set", "tuple", "list", "frozenset", "dict"} \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and not node.keywords and len(node.args) <= 1:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "dict" and node.func.attr == "fromkeys" \
                                and "dict" not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and "dict" not in local and "dict" not in params:
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id in {"str", "int", "float", "bytes", "repr", "ascii", "Decimal"} \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params:
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id == "next" \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and not node.keywords and len(node.args) in {1, 2}:
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id == "iter" \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and not node.keywords and len(node.args) == 1:
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id == "map" \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and not node.keywords and len(node.args) == 2 \
                                and isinstance(node.args[0], ast.Name) \
                                and node.args[0].id in {"len", "str", "int", "float", "bool", "bytes", "repr", "ascii", "ord", "chr", "hex", "oct", "bin", "abs"} \
                                and node.args[0].id not in binding_names_of[q] \
                                and node.args[0].id not in local and node.args[0].id not in params:
                            continue
                        if isinstance(node.func, ast.Attribute) and (
                                (isinstance(node.func.value, ast.Name) and node.func.value.id == "re" and node.func.attr in {"search", "match", "fullmatch", "sub", "split", "findall", "finditer", "escape", "subn"})
                                or node.func.attr in {"search", "match", "fullmatch", "findall", "finditer", "split", "escape", "sub", "subn"}
                        ):
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "shlex" and node.func.attr in {"quote", "join", "split", "shlex"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "textwrap" and node.func.attr in {"dedent", "indent", "fill", "shorten"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id in {"json", "yaml"} and node.func.attr in {"dump", "dumps", "load", "loads", "safe_dump", "safe_load"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "hashlib" and node.func.attr in {"sha256", "sha1", "md5", "blake2b", "blake2s"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "base64" and node.func.attr in {"b64decode", "b64encode", "urlsafe_b64decode", "urlsafe_b64encode"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "math" and node.func.attr in {
                                    "isfinite", "isnan", "isinf", "isclose", "floor", "ceil", "trunc",
                                    "fabs", "sqrt", "log", "log10", "log2", "exp"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "subprocess" and node.func.attr in {"Popen", "run", "check_call", "check_output", "call"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "tempfile" and node.func.attr in {"mkdtemp", "mkstemp", "TemporaryDirectory", "NamedTemporaryFile"}:
                            continue
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                                and node.func.value.id == "shutil" and node.func.attr in {"rmtree", "copy", "copy2", "copyfile", "move", "which"}:
                            continue
                        if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                                and node.func.value.id in MODEL_CLIENT_PACKAGES) \
                                or (isinstance(node.func, ast.Name) and node.func.id in {"Anthropic", "OpenAI"}):
                            continue
                        if (isinstance(node.func, ast.Name) and node.func.id in {"copy", "deepcopy"}
                            and node.func.id not in local and node.func.id not in params) \
                                or (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                                    and node.func.value.id == "copy" and node.func.attr in {"copy", "deepcopy"}):
                            continue
                        def _is_safe_key_expr(expr, lambda_params=frozenset()):
                            if isinstance(expr, ast.Constant):
                                return True
                            if isinstance(expr, ast.Name):
                                return expr.id in lambda_params or expr.id not in aliases
                            if isinstance(expr, (ast.Tuple, ast.List)):
                                return all(_is_safe_key_expr(e, lambda_params) for e in expr.elts)
                            if isinstance(expr, ast.UnaryOp):
                                return _is_safe_key_expr(expr.operand, lambda_params)
                            if isinstance(expr, ast.BinOp):
                                return _is_safe_key_expr(expr.left, lambda_params) and _is_safe_key_expr(expr.right, lambda_params)
                            if isinstance(expr, ast.BoolOp):
                                return all(_is_safe_key_expr(v, lambda_params) for v in expr.values)
                            if isinstance(expr, ast.Compare):
                                return _is_safe_key_expr(expr.left, lambda_params) and all(_is_safe_key_expr(c, lambda_params) for c in expr.comparators)
                            if isinstance(expr, ast.IfExp):
                                return _is_safe_key_expr(expr.test, lambda_params) and _is_safe_key_expr(expr.body, lambda_params) and _is_safe_key_expr(expr.orelse, lambda_params)
                            if isinstance(expr, ast.Subscript):
                                return _is_safe_key_expr(expr.value, lambda_params) and _is_safe_key_expr(expr.slice, lambda_params)
                            if isinstance(expr, ast.Attribute):
                                return _is_safe_key_expr(expr.value, lambda_params)
                            if isinstance(expr, ast.Call):
                                if isinstance(expr.func, ast.Name) and expr.func.id in {"len", "str", "int", "float", "bool", "repr", "ascii", "ord", "chr", "hex", "oct", "bin", "abs", "round", "min", "max", "sum", "tuple", "list", "set", "frozenset"} \
                                        and expr.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                        and expr.func.id not in local and expr.func.id not in params:
                                    return all(_is_safe_key_expr(a, lambda_params) for a in expr.args) and all(_is_safe_key_expr(kw.value, lambda_params) for kw in expr.keywords)
                                if isinstance(expr.func, ast.Attribute) and expr.func.attr in {"get", "lower", "upper", "strip", "lstrip", "rstrip", "casefold", "title", "startswith", "endswith", "split", "rsplit", "replace", "count", "find", "rfind"}:
                                    return _is_safe_key_expr(expr.func.value, lambda_params) and all(_is_safe_key_expr(a, lambda_params) for a in expr.args) and all(_is_safe_key_expr(kw.value, lambda_params) for kw in expr.keywords)
                            return False

                        def _is_safe_key_arg(kv):
                            if isinstance(kv, ast.Name) and kv.id in {"len", "str", "int", "repr", "float", "bool", "abs"} \
                                    and kv.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                    and kv.id not in local and kv.id not in params:
                                return True
                            if isinstance(kv, ast.Lambda):
                                lparams = {a.arg for a in kv.args.posonlyargs + kv.args.args + kv.args.kwonlyargs}
                                if kv.args.vararg:
                                    lparams.add(kv.args.vararg.arg)
                                if kv.args.kwarg:
                                    lparams.add(kv.args.kwarg.arg)
                                if any(not _is_safe_key_expr(d, frozenset()) for d in list(kv.args.defaults) + [d for d in kv.args.kw_defaults if d is not None]):
                                    return False
                                return _is_safe_key_expr(kv.body, frozenset(lparams))
                            return False

                        if isinstance(node.func, ast.Name) and node.func.id in {"sorted", "reversed", "enumerate"} \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and all(k.arg in {"reverse", "key", "start"} and (k.arg != "key" or _is_safe_key_arg(k.value)) for k in node.keywords):
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id in {"sum", "min", "max", "any", "all", "abs", "round"} \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and all(k.arg in {"start", "default", "key", "ndigits"} and (k.arg != "key" or _is_safe_key_arg(k.value)) for k in node.keywords):
                            continue
                        if isinstance(node.func, ast.Name) and node.func.id == "print" \
                                and node.func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                                and node.func.id not in local and node.func.id not in params \
                                and all(k.arg in {"sep", "end", "file", "flush"} for k in node.keywords):
                            continue
                        if (isinstance(node.func, ast.Name) and "classify" in node.func.id) \
                                or (isinstance(node.func, ast.Attribute) and "classify" in node.func.attr):
                            continue
                        if is_read_only_open_call(node) or is_http_call(node) or is_parser_call(node):
                            continue
                        if isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes", "write"} and node.args and actual is node.args[0]:
                            continue
                        if q is not None and str(q).endswith("schema_snapshot.py") and isinstance(node.func, ast.Name) and node.func.id == "read":
                            continue
                        if q is not None and str(q).endswith(_audit_evidence_modules):
                            continue
                    if may_reference(actual, context):
                        receiving.append(actual)
                if path_conversion(node) or detached_address(q, fn, node) or detached_record(q, fn, node) or detached_value_call(q, fn, node):
                    continue
                if not receiving:
                    continue
                callee_call = node
                is_partial = _is_real_repo_module(q) and ((isinstance(node.func, ast.Name) and node.func.id == "partial") or
                              (isinstance(node.func, ast.Attribute) and node.func.attr == "partial")) and bool(node.args)
                if is_partial:
                    receiving = [a for a in receiving if a is not node.args[0]]
                    if not receiving:
                        continue
                    callee_func = node.args[0]
                    if isinstance(callee_func, ast.Name) and callee_func.id in {
                            "len", "str", "int", "float", "bool", "bytes", "repr", "ascii",
                            "ord", "chr", "hex", "oct", "bin", "abs", "round", "hash", "id",
                            "type", "isinstance", "issubclass", "callable", "hasattr", "getattr",
                            "any", "all", "min", "max", "sum", "sorted", "reversed", "enumerate",
                            "zip", "map", "filter", "list", "tuple", "set", "frozenset", "dict",
                            "range", "slice", "iter", "next", "format", "open", "print"} \
                            and callee_func.id not in binding_names_of[q] and "*" not in binding_names_of[q] \
                            and callee_func.id not in local and callee_func.id not in params:
                        continue
                    callee_call = ast.Call(func=callee_func, args=node.args[1:], keywords=node.keywords)
                else:
                    callee_func = node.func
                hit = summary_callee(q, fn, callee_func)
                child = None
                callee_q = None
                callee_key = None
                is_meth = False
                if hit is not None:
                    callee_q = hit[0]
                    callee_key = hit
                    child = defs(hit[0])[hit[1]]
                elif _is_real_repo_module(q) and fn is not None and isinstance(callee_func, ast.Name):
                    scope_fn = fn
                    while scope_fn is not None:
                        local_defs = [s for s in scope_fn.body
                                      if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
                                      and s.name == callee_func.id]
                        if len(local_defs) == 1 and not local_defs[0].decorator_list:
                            if callee_func.id not in set(_params(scope_fn)) and not any(
                                    isinstance(target, ast.Name) and target.id == callee_func.id
                                    and isinstance(target.ctx, (ast.Store, ast.Del))
                                    for target in ast.walk(scope_fn)):
                                child = local_defs[0]
                                callee_q = q
                                callee_key = (q, f"{fn.name}.<locals>.{child.name}")
                                break
                        if q in parsed:
                            scope_fn = _enclosing_function(parsed[q][1], scope_fn)
                        else:
                            break
                    if child is None and q in parsed:
                        top_defs = [s for s in parsed[q][1].body
                                    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
                                    and s.name == callee_func.id]
                        if len(top_defs) == 1 and not top_defs[0].decorator_list:
                            if not any(
                                isinstance(s, (ast.Assign, ast.AnnAssign))
                                and any(isinstance(t, ast.Name) and t.id == callee_func.id
                                        for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))
                                for s in parsed[q][1].body
                            ):
                                scope_fn = fn
                                shadowed = False
                                while scope_fn is not None:
                                    if callee_func.id in set(_params(scope_fn)) | set(_local_writes(scope_fn)):
                                        shadowed = True
                                        break
                                    scope_fn = _enclosing_function(parsed[q][1], scope_fn)
                                if not shadowed:
                                    child = top_defs[0]
                                    callee_q = q
                                    callee_key = (q, child.name)
                elif _is_real_repo_module(q) and fn is not None and isinstance(callee_func, ast.Attribute) and isinstance(callee_func.value, ast.Name):
                    callee_q, child = resolve_method_callee(q, fn, callee_func)
                    if child is not None:
                        is_meth = bool(child.args.posonlyargs + child.args.args and (child.args.posonlyargs + child.args.args)[0].arg in {"self", "cls"})
                        callee_key = (callee_q, f"method.{child.name}")

                if child is None:
                    refusal(node, "unresolved or uncertain receiving callable")

                if callee_key in effect_stack:
                    refusal(node, "recursive receiving helper")
                def formal_only_writes_top_dict_keys(target_fn, formal_name):
                    effect_nodes(target_fn)
                    if formal_name not in set(_params(target_fn)) \
                            or formal_name in effect_unknown_bindings_of[id(target_fn)] \
                            or "*" in effect_unknown_bindings_of[id(target_fn)] \
                            or formal_name in _local_writes(target_fn):
                        return False
                    allowed_name_ids = set()
                    for stmt in effect_nodes(target_fn):
                        if isinstance(stmt, ast.Assign):
                            if any(isinstance(n, ast.Name) and n.id == formal_name for n in ast.walk(stmt.value)):
                                return False
                            for t in stmt.targets:
                                if isinstance(t, ast.Subscript) and isinstance(t.ctx, ast.Store) \
                                        and isinstance(t.value, ast.Name) and t.value.id == formal_name \
                                        and not any(isinstance(n, ast.Name) and n.id == formal_name for n in ast.walk(t.slice)):
                                    allowed_name_ids.add(id(t.value))
                    if not allowed_name_ids:
                        return False
                    return all(
                        id(n) in allowed_name_ids
                        for stmt in target_fn.body
                        for n in ast.walk(stmt)
                        if isinstance(n, ast.Name) and n.id == formal_name
                    )

                def is_outer_dict_top_key_write(actual, child_fn, formal_name):
                    return (
                        _is_real_repo_module(q)
                        and isinstance(actual, ast.Name)
                        and actual.id != name
                        and actual.id in uncertain
                        and actual.id not in context
                        and proven_container_kind(actual.id) == "dict"
                        and formal_only_writes_top_dict_keys(child_fn, formal_name)
                    )

                binding = _argument_parameters(child, callee_call, is_method=is_meth)
                receiving_ids = {id(a) for a in receiving}
                if _is_real_repo_module(q) and binding is not None:
                    bound_receiving_formals = [(act, p) for act, names in binding if id(act) in receiving_ids for p in names]
                    if bound_receiving_formals and not any(
                        formal_has_receiving_effects(callee_q, child, p)
                        and not is_outer_dict_top_key_write(act, child, p)
                        for act, p in bound_receiving_formals
                    ):
                        continue
                if is_partial:
                    refusal(node, "unresolved or uncertain receiving callable")
                if binding is None or child.args.vararg is not None or child.args.kwarg is not None \
                        or any(isinstance(a, ast.Starred) for a in callee_call.args) \
                        or any(k.arg is None for k in callee_call.keywords) \
                        or any(len(names) != 1 for _, names in binding):
                    refusal(node, "ambiguous argument/formal binding")
                assigned = [next(iter(names)) for _, names in binding]
                if len(assigned) != len(set(assigned)):
                    refusal(node, "duplicate argument/formal binding")
                positional = child.args.posonlyargs + child.args.args
                child_defaults = {p.arg: value for p, value in zip(
                    positional[len(positional) - len(child.args.defaults):], child.args.defaults)}
                child_defaults.update({p.arg: value for p, value in zip(
                    child.args.kwonlyargs, child.args.kw_defaults) if value is not None})
                positional_params = positional[1:] if is_meth and positional and positional[0].arg in {"self", "cls"} else positional
                expected_params = set(p.arg for p in positional_params) | set(p.arg for p in child.args.kwonlyargs)
                if expected_params - set(assigned) - set(child_defaults):
                    refusal(node, "missing required helper argument")
                receiving_ids = {id(a) for a in receiving}
                for actual, names in binding:
                    if id(actual) in receiving_ids:
                        formal_name = next(iter(names))
                        if formal_has_receiving_effects(callee_q, child, formal_name) \
                                and not is_outer_dict_top_key_write(actual, child, formal_name):
                            if not isinstance(actual, ast.Name) or actual.id in uncertain or actual.id in context:
                                refusal(node, "container passed through an unmodeled projection")

                targets = {next(iter(names)) for actual, names in binding
                           if id(actual) in receiving_ids
                           and isinstance(actual, ast.Name) and actual.id in aliases
                           and container_origins(actual.id)[0] != {"scalar"}
                           and formal_has_receiving_effects(callee_q, child, next(iter(names)))
                           and not is_outer_dict_top_key_write(actual, child, next(iter(names)))}
                if not targets:
                    continue
                child_kinds = {formal: container_kind(actual.id) for actual, names in binding
                               for formal in (next(iter(names)),)
                               if formal in targets}
                bindings = {next(iter(names)): (lambda m, p, actual=actual: walk(actual, m, p))
                            for actual, names in binding}

                if mode == "text":
                    spans.setdefault(callee_q, {}).setdefault(
                        (child.lineno, child.end_lineno), f"{child.name}() (writes model-text local container)")
                flow(callee_q, child, (), why, project, bindings, child_defaults,
                     targets, effect_stack + (callee_key,), value_mode=mode, effect_kinds=child_kinds,
                     primitive_formals=call_primitives(node, callee_key) if hit is not None else frozenset(),
                     json_formals=call_json_facts(node, callee_key) if hit is not None else frozenset())

        def walk(e, mode, project=()):
            # A selector supplies an address or key, not the selected text.
            # Ordinary data still conservatively follows constants (#4990).
            if e is None or mode == "selector":
                return
            project = normalized_projection(project)
            if not admit_projection(seen, (id(e), mode), project):
                return
            if mode == "text" and (isinstance(e, ast.JoinedStr) or (
                    isinstance(e, ast.Constant) and isinstance(e.value, str))):
                label = f"{where} ({why})"
                literals.setdefault(q, {}).setdefault((e.lineno, e.end_lineno), label)
                if _prose(e):
                    wrote.setdefault(q, {})[label] = None
            if isinstance(e, ast.Name):
                if e.id in local:
                    for v in local[e.id]:
                        walk(v, mode, project)
                    effects(e.id, mode, project)
                if e.id in bound:
                    bound[e.id](mode, project)
                elif e.id in defaults:
                    # Eligible helpers are direct module definitions. Defaults
                    # are evaluated there, not in the function's local scope.
                    flow(q, None, (defaults[e.id],), why, project, value_mode=mode)
                elif e.id not in local and e.id not in params:
                    if e.id in consts(q):
                        mark_constant(q, e.id, why, project)
                    else:
                        target, attr = binds(q).get(e.id, (None, None))
                        if target is not None and attr:
                            mark_constant(target, attr, why, project)
                return
            if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name):
                if e.value.id not in local and e.value.id not in params:
                    target, attr = binds(q).get(e.value.id, (None, None))
                    if target is not None and attr is None:
                        mark_constant(target, e.attr, why, project)
                    return
            if isinstance(e, ast.Call):
                imported_text_helper = text_helper_alias(q, fn, e.func)
                # A proven local import also overrides a same-spelled module
                # function that the historical scope-insensitive callee table
                # would otherwise select. Other callee resolution is unchanged.
                hit = None if imported_text_helper else callee(q, e.func)
                selectors = selector_arguments(q, fn, e, hit)
                method = isinstance(e.func, ast.Attribute)
                text_args = (method and e.func.attr in STR_TEXT_METHODS) or (
                    hit is None and (_attr_or_name(e.func) in TEXT_CARRYING_CALLS
                                     or imported_text_helper))
                indexes, names, star_from, any_kw = set(), set(), None, False
                actual_projects = {}
                certain = hit is not None and summary_callee(q, fn, e.func) == hit
                if mode == "text" and hit is not None:
                    mark_function(hit[0], hit[1], why, project, call_primitives(e, hit), call_json_facts(e, hit))
                    indexes, names, star_from, any_kw = carried(hit)
                    # A nominal old callee is not authority to narrow
                    # mapping depth after decoration/rebinding/shadowing.
                    # Keep its historical argument projection unless the
                    # existing strict body/binding gate authenticates it.
                    if certain:
                        actual_projects = argument_projections(
                            defs(hit[0])[hit[1]], e, projected_carried(hit, project))
                unprojected = text_args or (hit is not None and not certain)
                if method:
                    receiver_project = project
                    if hit is None and e.func.attr in {"keys", "items"}:
                        receiver_project = (True,)
                    elif hit is None and e.func.attr == "values":
                        receiver_project = (False,) + project
                    walk(e.func.value, "selector" if e.func.attr in FILE_READ_METHODS else mode,
                         receiver_project)
                for i, a in enumerate(e.args):
                    starred = isinstance(a, ast.Starred)
                    carries = text_args or i in indexes or (star_from is not None and i >= star_from) or (
                        starred and (any(j >= i for j in indexes) or star_from is not None))
                    actual = a.value if starred else a
                    actual_project = actual_projects.get(id(actual), project) if carries else project
                    walk(actual, "selector" if id(actual) in selectors else (mode if carries else "data"),
                         (True,) if (carries and unprojected) else actual_project)
                for k in e.keywords:
                    carries = k.arg in names or (any_kw and k.arg not in names) or (k.arg is None and bool(names))
                    actual_project = actual_projects.get(id(k.value), project) if carries else project
                    walk(k.value, "selector" if id(k.value) in selectors else (mode if carries else "data"),
                         (True,) if (carries and unprojected) else actual_project)
                return
            if isinstance(e, ast.IfExp):
                walk(e.body, mode, project)
                walk(e.orelse, mode, project)
                return
            if isinstance(e, (ast.Compare, ast.Lambda)):
                return
            if isinstance(e, ast.Subscript):
                walk(e.value, mode, (False,) + project)
                walk(e.slice, "selector")
                return
            if isinstance(e, ast.Dict):
                emit_keys = bool(project and project[0])
                values_project = project if emit_keys or not project else project[1:]
                for k, v in zip(e.keys, e.values):
                    if k is None:  # **mapping retains this mapping level.
                        walk(v, mode, project)
                    else:
                        walk(k, mode if emit_keys else "data")
                        walk(v, mode, values_project)
                return
            for child in ast.iter_child_nodes(e):
                walk(child, mode, project)

        for name in effect_names:
            effects(name, value_mode, projection, formal=True)
        for e in exprs:
            walk(e, value_mode, projection)

    hook_sinks = []
    for rel, p in sorted(controllers.items()):
        tree = parsed[p][1]
        for name, fn in defs(p).items():
            if MODEL_TEXT_FUNCTION.match(name):
                mark_function(p, name, "renders model text")
        # a function of another module the controller calls, named for the
        # text it renders (`audit_batch_context.render_worker_context`, whose
        # result a controller writes for its native child to read, #4085)
        for c in ast.walk(tree):
            hit = callee(p, c.func) if isinstance(c, ast.Call) else None
            if hit is not None and hit[0] != p and MODEL_TEXT_FUNCTION.match(hit[1]):
                mark_function(hit[0], hit[1], f"renders model text for the controller call at {rel}:{c.lineno}")
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
    # The supplied sinks certify particular request fields/model-file values.
    # Only their immediate owning call is a terminal consumer; do not infer
    # that every call surrounding an arbitrary flow seed is harmless.
    for q, fn, exprs, why in sinks:
        if q in parsed:
            if q not in text_helper_parents_of:
                text_helper_parents_of[q] = _parents(parsed[q][1])
            parents = text_helper_parents_of[q]
            consumers = set()
            if isinstance(exprs, _RequestInputValues):
                if exprs.unresolved_identity:
                    raise ConfigError(f"unsupported effect in request construction at "
                                      f"{_rel(root, q)}:{exprs.call.lineno}: "
                                      "request constructor identity can change across executions")
                if exprs.unresolved_spread:
                    raise ConfigError(f"unsupported effect in request construction at "
                                      f"{_rel(root, q)}:{exprs.call.lineno}: "
                                      "request arguments have no exact literal field mapping")
                # Discovery authenticated the lexical constructor and mapped
                # each exact literal spread to its request field. Grant only
                # that Call terminal status, never an inferred ancestor.
                consumers.add(id(exprs.call))
            for value in (() if isinstance(exprs, _RequestInputValues) else exprs):
                owner = parents.get(id(value))
                if isinstance(owner, (ast.keyword, ast.Starred)):
                    owner = parents.get(id(owner))
                if isinstance(owner, ast.Call):
                    actuals = [a.value if isinstance(a, ast.Starred) else a for a in owner.args]
                    actuals += [k.value for k in owner.keywords]
                    if any(value is actual for actual in actuals):
                        consumers.add(id(owner))
            flow(q, fn, exprs, why, terminal_consumers=frozenset(consumers))
    while todo:
        q, name, projection, primitive_formals, json_formals = todo.pop()
        fn = defs(q)[name]
        flow(q, fn, _results(fn), f"its value reaches {name}()", projection,
             primitive_formals=primitive_formals, json_formals=json_formals)
    # a literal inside a span already found adds nothing
    for q, sp in literals.items():
        for (a, b), label in sp.items():
            if not any(lo <= a and b <= hi for lo, hi in spans.get(q, {})):
                spans.setdefault(q, {}).setdefault((a, b), label)
    return ({_rel(root, q): sorted((a, b, label) for (a, b), label in sp.items())
             for q, sp in spans.items() if _is_inside(q, root)},
            {_rel(root, q): list(w) for q, w in wrote.items() if _is_inside(q, root)})


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


# --------------------------------------------------------------------------
# which modules write model-facing text, derived (#4085)


def derive_request_type(root: Path) -> dict:
    """The request the runner sends (#4085): the class `build_phase` returns
    a construction of, directly or through a local (`req = PhaseRequest(...)`,
    `return req`), with its fields in order. Not found, two classes, or a
    request type without every field `REQUEST_TEXT_FIELDS` names, is not
    derived."""
    tree = _tree(root / RUNNER)
    build = _function(tree, "build_phase")
    if build is None:
        raise _not_derived("the request the runner sends", "api_runner.py defines no build_phase()")
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    local = _local_values(build)
    returned = [r.value for r in ast.walk(build) if isinstance(r, ast.Return) and r.value is not None]
    returned += [v for r in returned if isinstance(r, ast.Name) for v in local.get(r.id, [])]
    found = sorted({r.func.id for r in returned if isinstance(r, ast.Call) and isinstance(r.func, ast.Name)
                    and r.func.id in classes})
    if len(found) != 1:
        raise _not_derived("the request the runner sends",
                           f"build_phase returns a construction of {found or 'no class api_runner.py defines'}")
    fields = [s.target.id for s in classes[found[0]].body
              if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]
    missing = [f for f in REQUEST_TEXT_FIELDS if f not in fields]
    if missing:
        raise _not_derived("the request the runner sends", f"{found[0]} has no field {', '.join(missing)}")
    return {"class": found[0], "fields": fields, "text_fields": list(REQUEST_TEXT_FIELDS)}


def model_input_files(root: Path, playbooks) -> dict[str, list[str]]:
    """The files a run reads as model input, by the file name that follows
    the project (#4085): every arm's bundle in `cli/api.py` ARMS
    (`{p}_healthsheet_only.txt` -> `_healthsheet_only.txt`) and every
    templated file under the input tree that a playbook names
    (`data/preprocessed/chunks/{PROJECT}_chunks.yaml` -> `_chunks.yaml`):
    suffix -> what names it. An arm without a bundle pattern is not
    derived."""
    arms = _module_constants(root / CLI_API).get("ARMS")
    if not isinstance(arms, dict) or not arms:
        raise _not_derived("the model input files", "cli/api.py ARMS is not a module-level dict literal")
    out: dict[str, set] = {}
    for arm, row in arms.items():
        bundle = row[2] if isinstance(row, tuple) and len(row) > 2 else None
        if not isinstance(bundle, str) or "{p}" not in bundle:
            raise _not_derived("the model input files", f"ARMS[{arm!r}] has no `{{p}}...` bundle pattern")
        out.setdefault(bundle.split("{p}", 1)[1], set()).add(f"the {arm} arm's bundle")
    for p in playbooks:
        if hasattr(p, "read_text"):
            for m in TEMPLATED_INPUT.finditer(p.read_text(encoding="utf-8")):
                out.setdefault(m.group(1), set()).add(_rel(root, p))
    return {k: sorted(v) for k, v in sorted(out.items())}


def _eager_annotations(tree):
    return not any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
                   and any(alias.name == "annotations" for alias in node.names)
                   for node in tree.body)


def _own_nodes(fn, *, eager_annotations=True):
    """Executable function-body nodes, including nested definition headers.

    Nested function/method/lambda bodies are deferred. Defaults, decorators,
    class bases/keywords and class bodies run while defining them. Function
    and class annotations obey the module's postponed-annotation declaration;
    local variable annotations inside functions are never evaluated here.
    """
    todo = [(node, False) for node in fn.body]
    while todo:
        node, class_body = todo.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            children = list(args.defaults) + [value for value in args.kw_defaults if value is not None]
            if not isinstance(node, ast.Lambda):
                children += node.decorator_list
                if eager_annotations:
                    parameters = args.posonlyargs + args.args + args.kwonlyargs
                    parameters += [arg for arg in (args.vararg, args.kwarg) if arg is not None]
                    children += [arg.annotation for arg in parameters if arg.annotation is not None]
                    if node.returns is not None:
                        children.append(node.returns)
            todo += [(child, class_body) for child in children]
        elif isinstance(node, ast.ClassDef):
            todo += [(child, class_body) for child in node.decorator_list + node.bases + node.keywords]
            todo += [(child, True) for child in node.body]
        elif isinstance(node, ast.AnnAssign):
            children = [node.target] + ([node.value] if node.value is not None else [])
            if class_body and eager_annotations:
                children.append(node.annotation)
            todo += [(child, class_body) for child in children]
        else:
            todo += [(child, class_body) for child in ast.iter_child_nodes(node)]


def _file_writes(fn, *, eager_annotations=True) -> list[tuple[ast.AST, ast.AST, ast.Call]]:
    """(target, value, call) for every file a function itself writes
    (#4085): `target.write_text(value)`, and `handle.write(value)`,
    `json.dump(value, handle)` or `yaml.safe_dump(value, handle)` where a
    `with` binds `handle` to `open(target, ...)` or `target.open(...)`. A
    nested function's writes are its own."""
    handles = {}
    nodes = list(_own_nodes(fn, eager_annotations=eager_annotations))
    for n in nodes:
        if isinstance(n, (ast.With, ast.AsyncWith)):
            for item in n.items:
                c = item.context_expr
                if not (isinstance(item.optional_vars, ast.Name) and isinstance(c, ast.Call)):
                    continue
                if isinstance(c.func, ast.Name) and c.func.id == "open" and c.args:
                    handles[item.optional_vars.id] = c.args[0]
                elif isinstance(c.func, ast.Attribute) and c.func.attr == "open":
                    handles[item.optional_vars.id] = c.func.value
    out = []
    for n in nodes:
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.args):
            continue
        f = n.func
        if f.attr == "write_text":
            out.append((f.value, n.args[0], n))
        elif f.attr == "write" and isinstance(f.value, ast.Name) and f.value.id in handles:
            out.append((handles[f.value.id], n.args[0], n))
        elif f.attr in {"dump", "safe_dump"} and len(n.args) > 1 and isinstance(n.args[1], ast.Name) \
                and n.args[1].id in handles:
            out.append((handles[n.args[1].id], n.args[0], n))
    return out


def _resolve_call(root: Path, parsed: dict, index: dict, q: Path, func):
    """(module, function node) a call in module `q` names: a function of
    the module, one imported by name, or one read through an imported
    module; None otherwise."""
    tree = parsed[q][1]
    defs = _function_defs(tree)
    if isinstance(func, ast.Name):
        if func.id in defs:
            return q, defs[func.id]
        target, attr = _bindings(root, q, tree, index).get(func.id, (None, None))
        if target is not None and attr and target in parsed:
            fn = _function_defs(parsed[target][1]).get(attr)
            return (target, fn) if fn is not None else None
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        target, attr = _bindings(root, q, tree, index).get(func.value.id, (None, None))
        if target is not None and attr is None and target in parsed:
            fn = _function_defs(parsed[target][1]).get(func.attr)
            return (target, fn) if fn is not None else None
    return None


#: Path calls whose result ends in their last argument's name
#: (`Path(name)`, `os.path.join(d, name)`, `x.with_name(name)`), or in their
#: argument's suffix (`x.with_suffix('.tmp')`).
_PATH_TAIL_CALLS = frozenset({"Path", "PurePath", "PurePosixPath", "str", "join", "with_name", "with_suffix"})


def _file_names(root: Path, parsed: dict, index: dict, q: Path, fn, expr) -> set[str]:
    """The literal text a write's target path can end with (#4085): the last
    part of the path expression (`d / name`, `Path(name)`, `x.with_name(name)`,
    `os.path.join(d, name)`), each alternative of an `or` or a conditional,
    through the function's locals, the constants it names (of its module, or
    imported by name) and the results of the functions it calls, each once;
    an f-string ends with its last part (`f"{project}_chunks.yaml"` ->
    `_chunks.yaml`, `f"{project}{BUNDLE_SUFFIX}"` -> the constant's value).
    A path read off an object (`spec.full_path`) or a parameter ends in
    nothing the scan can see."""
    out: set[str] = set()
    seen: set[int] = set()
    todo = [(q, fn, expr)]
    while todo:
        q, fn, e = todo.pop()
        if e is None or id(e) in seen:
            continue
        seen.add(id(e))
        tree = parsed[q][1]
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            out.add(e.value)
        elif isinstance(e, ast.JoinedStr) and e.values:
            last = e.values[-1]
            todo.append((q, fn, last.value if isinstance(last, ast.FormattedValue) else last))
        elif isinstance(e, ast.BinOp) and isinstance(e.op, (ast.Div, ast.Add)):
            todo.append((q, fn, e.right))
        elif isinstance(e, ast.BoolOp):
            todo += [(q, fn, v) for v in e.values]
        elif isinstance(e, ast.IfExp):
            todo += [(q, fn, e.body), (q, fn, e.orelse)]
        elif isinstance(e, ast.Name):
            local = _local_values(fn) if fn is not None else {}
            consts = _module_assignments(tree)
            if e.id in local:
                todo += [(q, fn, v) for v in local[e.id]]
            elif e.id in consts:
                todo.append((q, None, consts[e.id].value))
            else:
                target, attr = _bindings(root, q, tree, index).get(e.id, (None, None))
                if target is not None and attr and target in parsed:
                    there = _module_assignments(parsed[target][1])
                    if attr in there:
                        todo.append((target, None, there[attr].value))
        elif isinstance(e, ast.Call):
            name = _attr_or_name(e.func)
            if name in _PATH_TAIL_CALLS and e.args:
                todo.append((q, fn, e.args[-1]))
            else:
                hit = _resolve_call(root, parsed, index, q, e.func)
                if hit is not None:
                    todo += [(hit[0], hit[1], r) for r in _results(hit[1])]
    return out


class _RequestInputValues(list):
    """Request fields with their exact constructor proof, within a sink tuple."""

    def __init__(self, values, call, unresolved_spread=False):
        super().__init__(values)
        self.call = call
        self.unresolved_spread = unresolved_spread
        self.unresolved_identity = False


def _request_constructors(root, q, tree, index, runner, cls):
    """Authenticate direct class/module imports in their actual lexical scope.

    This adds no authority for aliases, competing bindings or unknown classes.
    Defaults/decorators are evaluated outside the body they help define.
    """
    parents = _parents(tree)
    scopes, imported, member_writes = {}, {}, []
    written_identities = []
    scope_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                   ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    comprehensions = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

    def inside(node, ancestor):
        while node is not None:
            if node is ancestor:
                return True
            node = parents.get(id(node))
        return False

    def scope_of(node):
        child, parent = node, parents.get(id(node))
        while parent is not None:
            if isinstance(parent, scope_types):
                if isinstance(parent, comprehensions):
                    if not inside(node, parent.generators[0].iter):
                        return parent
                elif isinstance(parent, ast.Lambda):
                    if isinstance(node, ast.arg) or child is parent.body:
                        return parent
                elif isinstance(node, ast.arg) or any(child is statement for statement in parent.body):
                    return parent
            child, parent = parent, parents.get(id(parent))
        return None

    def bind(scope, name, node):
        if name:
            scopes.setdefault(scope, {}).setdefault(name, []).append(node)

    for node in ast.walk(tree):
        scope = scope_of(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bind(scope, node.name, node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bind(scope, alias.asname or (alias.name.split('.')[0]
                     if isinstance(node, ast.Import) else alias.name), node)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            parent = parents.get(id(node))
            if isinstance(parent, ast.NamedExpr) and parent.target is node:
                # Assignment expressions inside comprehensions bind the
                # containing scope, unlike the comprehension's own targets.
                while isinstance(scope, comprehensions):
                    scope = scope_of(scope)
            bind(scope, node.id, node)
        elif isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
            member_writes.append((scope, _holder(node), node))
        elif isinstance(node, ast.arg):
            bind(scope, node.arg, node)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bind(scope, node.name, node)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            for name in node.names:
                bind(scope, name, node)
                if isinstance(node, ast.Global):
                    bind(None, name, node)
                else:
                    outer = scope_of(scope)
                    while outer is not None:
                        if isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                            bind(outer, name, node)
                        outer = scope_of(outer)
        elif type(node).__name__ in {'MatchAs', 'MatchStar'} and node.name:
            bind(scope, node.name, node)
        elif type(node).__name__ == 'MatchMapping' and node.rest:
            bind(scope, node.rest, node)

    def import_target(binding, name):
        if not isinstance(binding, (ast.Import, ast.ImportFrom)):
            return None
        if id(binding) not in imported:
            imported[id(binding)] = _bindings(root, q, ast.Module(body=[binding], type_ignores=[]), index)
        return imported[id(binding)].get(name)

    # Attribute writes do not create a Python local binding. Charge them to
    # the lexical import/class they can replace, including a module import
    # used by another function after the writing function runs.
    for scope, name, node in member_writes:
        while scope is not None and name not in scopes.get(scope, {}):
            current, scope = scope, scope_of(scope)
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                while isinstance(scope, ast.ClassDef):
                    scope = scope_of(scope)
        for binding in scopes.get(scope, {}).get(name, ()):
            target = import_target(binding, name)
            if target == (runner, None):
                first = node
                while isinstance(getattr(first, 'value', None), (ast.Attribute, ast.Subscript)):
                    first = first.value
                if isinstance(first, ast.Attribute) and first.attr == cls:
                    kind = 'namespace' if node is first else 'class'
                    written_identities.append((kind, node))
                elif isinstance(first, ast.Attribute) and first.attr == '__dict__':
                    written_identities.append(('namespace', node))
            elif target == (runner, cls):
                written_identities.append(('class', node))
            elif q == runner and isinstance(binding, ast.ClassDef) and binding.name == cls:
                written_identities.append(('class', node))
        bind(scope, name, node)

    def binding_for(expression, preserve_member_identity=False):
        name = expression.id
        scope = scope_of(expression)
        while True:
            names = scopes.get(scope, {})
            if '*' in names:
                return None
            entries = names.get(name, ())
            if preserve_member_identity:
                entries = [entry for entry in entries if not (
                    isinstance(entry, (ast.Attribute, ast.Subscript))
                    and isinstance(entry.ctx, (ast.Store, ast.Del)))]
            if entries:
                if len(entries) != 1:
                    return None
                binding = entries[0]
                body = tree.body if scope is None else getattr(scope, 'body', ())
                if not isinstance(body, list) or not any(binding is statement for statement in body):
                    return None
                if scope is not None and getattr(binding, 'lineno', 0) >= expression.lineno:
                    return None
                return binding
            if scope is None:
                return None
            current, scope = scope, scope_of(scope)
            # Function/lambda bodies do not capture class-local attributes.
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                while isinstance(scope, ast.ClassDef):
                    scope = scope_of(scope)

    def captured_before(binding, write):
        """A captured class survives a later module namespace replacement."""
        capture_scope, write_scope = scope_of(binding), scope_of(write)
        # A local import executes again on a later invocation and can then
        # capture a replacement installed by an earlier call. Only a module
        # capture has the source-level lifetime needed for this exception.
        if capture_scope is not None:
            return False
        boundary = write
        while write_scope is not capture_scope:
            if write_scope is None:
                return False
            boundary, write_scope = write_scope, scope_of(write_scope)
        return binding.lineno < boundary.lineno

    def imported_binding_for(expression, target):
        # Member writes can invalidate the import's object without rebinding
        # its lexical name. Retain that possible identity for an explicit
        # refusal; ordinary competing lexical bindings remain non-sinks.
        scope = scope_of(expression)
        while True:
            names = scopes.get(scope, {})
            if '*' in names:
                return None
            entries = names.get(expression.id, ())
            if entries:
                imports = [entry for entry in entries
                           if import_target(entry, expression.id) == target]
                if len(imports) != 1 or any(entry is not imports[0] and not (
                        isinstance(entry, (ast.Attribute, ast.Subscript))
                        and isinstance(entry.ctx, (ast.Store, ast.Del))) for entry in entries):
                    return None
                binding = imports[0]
                body = tree.body if scope is None else getattr(scope, 'body', ())
                if not isinstance(body, list) or binding not in body:
                    return None
                if scope is not None and binding.lineno >= expression.lineno:
                    return None
                return binding
            if scope is None:
                return None
            current, scope = scope, scope_of(scope)
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                while isinstance(scope, ast.ClassDef):
                    scope = scope_of(scope)

    def module_statement(node):
        while parents.get(id(node)) is not tree:
            node = parents.get(id(node))
            if node is None:
                return None
        return node

    def before_all_writes(call):
        # A direct module execution before every possible write keeps the
        # original constructor. Function bodies may execute repeatedly.
        if scope_of(call) is not None:
            return False
        boundary = module_statement(call)
        return boundary is not None and all(
            (statement := module_statement(write)) is not None
            and boundary.lineno < statement.lineno
            for _, write in written_identities)

    def definitely_replaced(binding, call, captured):
        # A direct unconditional namespace replacement with a known plain
        # function is not a request constructor. Keep this narrow: unknown
        # values, class-object writes and uncertain timing require refusal.
        if captured:
            if scope_of(binding) is not None:
                return False
            boundary = binding
        else:
            boundary = module_statement(call)
        if boundary is None:
            return False
        for kind, write in written_identities:
            assignment = parents.get(id(write))
            if kind != 'namespace' or scope_of(write) is not None \
                    or assignment not in tree.body \
                    or not isinstance(assignment, (ast.Assign, ast.AnnAssign)) \
                    or not isinstance(write, ast.Attribute) or write.attr != cls \
                    or not isinstance(assignment.value, ast.Name) \
                    or assignment.lineno >= boundary.lineno:
                return False
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            if len(targets) != 1 or targets[0] is not write:
                return False
            definitions = scopes.get(None, {}).get(assignment.value.id, ())
            if len(definitions) != 1 or not isinstance(definitions[0], (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    or definitions[0] not in tree.body or definitions[0].decorator_list:
                return False
        return bool(written_identities)

    def identity(binding, call, captured):
        if not written_identities or before_all_writes(call):
            return True
        if captured and all(kind == 'namespace' and captured_before(binding, write)
                            for kind, write in written_identities):
            return True
        if definitely_replaced(binding, call, captured):
            return False
        return None

    calls = []
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        expression = call.func
        state = False
        if isinstance(expression, ast.Name):
            binding = imported_binding_for(expression, (runner, cls))
            if binding is not None:
                state = identity(binding, call, True)
            else:
                binding = binding_for(expression, preserve_member_identity=True)
                if q == runner and expression.id == cls and isinstance(binding, ast.ClassDef) \
                        and binding.name == cls and binding in tree.body:
                    state = identity(binding, call, False)
        elif isinstance(expression, ast.Attribute) and expression.attr == cls \
                and isinstance(expression.value, ast.Name):
            binding = imported_binding_for(expression.value, (runner, None))
            if binding is not None:
                state = identity(binding, call, False)
        if state is not False:
            calls.append((call, state is None))
    return calls


def _request_input_values(call, fields):
    """Map exact literal expansions to fields; defer uncertain spreads to flow."""
    positional, keywords, uncertain = [], [], False
    for argument in call.args:
        if isinstance(argument, ast.Starred):
            if isinstance(argument.value, (ast.Tuple, ast.List)) and not any(
                    isinstance(value, ast.Starred) for value in argument.value.elts):
                positional.extend(argument.value.elts)
            else:
                uncertain = True
        else:
            positional.append(argument)
    for keyword in call.keywords:
        if keyword.arg is None:
            mapping = keyword.value
            if isinstance(mapping, ast.Dict) and all(isinstance(key, ast.Constant)
                    and type(key.value) is str for key in mapping.keys):
                keywords.extend((key.value, value) for key, value in zip(mapping.keys, mapping.values))
            else:
                uncertain = True
        else:
            keywords.append((keyword.arg, keyword.value))
    names = [name for name, _ in keywords]
    if len(positional) > len(fields) or len(names) != len(set(names)) \
            or any(name not in fields or name in fields[:len(positional)] for name in names):
        uncertain = True
    if uncertain:
        # Preserve discovery metadata even when sinks are disabled. Active
        # text flow refuses instead of granting this call terminal authority.
        values = [a.value if isinstance(a, ast.Starred) else a for a in call.args]
        values += [keyword.value for keyword in call.keywords]
        return _RequestInputValues(values, call, unresolved_spread=True)
    values = [value for field, value in zip(fields, positional) if field in REQUEST_TEXT_FIELDS]
    values += [value for field, value in keywords if field in REQUEST_TEXT_FIELDS]
    return _RequestInputValues(values, call)


def model_input_sinks(root: Path, parsed: dict, index: dict, playbooks, upstream) -> tuple[list, dict]:
    """The text that reaches a model other than through a controller (#4085),
    as data-flow sinks (module, function, expressions, why) for `text_flow`:

    - what every request the runner sends carries: each construction, in
      any module, of the request type `build_phase` returns
      (`derive_request_type`), with the values it is given for
      `REQUEST_TEXT_FIELDS` (its system prompt, cached blocks and messages);
    - what a package function writes to a model-input file
      (`model_input_files`: an arm's bundle, a file a playbook has the model
      read from the input tree), recognised by the text the write's target
      path ends with (`_file_names`: `chunking.write_manifest_for` writes to
      `manifest_for(...)`, which ends in `f"{stem}_chunks.yaml"`);
    - what an upstream input step (`upstream`, the modules the `d4d
      download` group imports) writes: it writes the input tree, the
      documents a bundle is concatenated from.

    Returns (sinks, facts)."""
    request = derive_request_type(root)
    inputs = model_input_files(root, playbooks)
    runner = _resolved(root / RUNNER)
    cls, fields = request["class"], request["fields"]
    sinks, requests, writers = [], [], []
    for q, (text, tree) in sorted(parsed.items()):
        rel = _rel(root, q)
        writes = rel.startswith("src/data_sheets_schema/") or rel in upstream
        if cls in text:
            for call, uncertain_identity in _request_constructors(root, q, tree, index, runner, cls):
                values = _request_input_values(call, fields)
                values.unresolved_identity = uncertain_identity
                requests.append(f"{rel}:{call.lineno}")
                sinks.append((q, _innermost_function(tree, call.lineno), values,
                              f"sent in a {cls} at {rel}:{call.lineno}"))
        if not writes:
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for target, value, call in _file_writes(fn, eager_annotations=_eager_annotations(tree)):
                where = f"{rel}:{call.lineno}"
                if rel in upstream:
                    writers.append(where)
                    sinks.append((q, fn, [value], f"written by the upstream input step at {where}"))
                    continue
                ends = _file_names(root, parsed, index, q, fn, target)
                hit = sorted(s for s in inputs if any(name.endswith(s) for name in ends))
                if hit:
                    writers.append(where)
                    sinks.append((q, fn, [value], f"written to a `*{hit[0]}` model input at {where}"))
    return sinks, {"request": request, "model_input_files": inputs, "requests": requests, "writers": writers}


def derive_model_facing(wrote: dict[str, list[str]]) -> dict[str, list[str]]:
    """The top-level `data_sheets_schema` modules whose text reaches a model
    (#4085): each module the data flow (`text_flow`) carried one of its own
    string literals from into model text, with what carried it. A module
    that only passes on what it is given, or whose literals are punctuation
    and whitespace (a separator, a rule line), writes none."""
    out: dict[str, list[str]] = {}
    for rel, labels in sorted(wrote.items()):
        name = _package_module_name(Path(rel))
        if name is not None and rel.startswith("src/data_sheets_schema/"):
            out.setdefault(name, []).extend(labels)
    return out


def discover(root: Path) -> tuple[Surfaces, dict]:
    root = _resolved(root)
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

    facts["offline_draft_surfaces"] = list(OFFLINE_DRAFT_MODULES)
    for rel in OFFLINE_DRAFT_MODULES:
        if root / rel not in parsed:
            raise ConfigError(f"declared offline draft surface is missing or unreadable: {rel}")
        s.add(rel, "offline_draft", "model_facing", "offline draft",
              "explicit source-heading prompt-text builder; no provider or live condition", runs=True)

    # ---- api: runner closure, conditions, evidence protocols (the closure's
    # roles wait for the derivation of which modules write model text)
    api_closure = _package_closure(root, ["data_sheets_schema.cli.api", "data_sheets_schema.api_runner"])
    facts["api_closure"] = [_rel(root, p) for p in api_closure]
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
        if (root / rel).exists() and rel not in s.files and rel not in facts["api_closure"]:
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

    # ---- text a model receives, by data flow (#4054, #4085): from the
    # controllers' sinks, the runner's requests and the model-input writes.
    # A top-level package module whose own text it carries there is
    # model-facing (`derive_model_facing`), before any closure is given roles.
    playbook_files = sorted(p for p in (root / ".claude/commands").glob("d4d-*.md") if p.is_file())
    sinks, facts["model_input"] = model_input_sinks(root, parsed, index, playbook_files, set(shared))
    spans, wrote = text_flow(root, parsed, index, controllers, sinks)
    derived = derive_model_facing(wrote)
    for p in api_closure:
        s.add(_rel(root, p), "api", _module_role(p, derived), "live", "import closure of cli/api.py + api_runner",
              runs=False)

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
        s.add(_rel(root, p), "native_agentic", _module_role(p, derived), "live",
              "closure of agentic_runtime, the CLI groups the playbooks run and the controllers' imports", runs=False)
    # a CLI group run only by an exposed text, or by a controller (#4091)
    for approach, gs in sorted(cli_groups.items()):
        for g, by in sorted(gs.items()):
            if approach == "native_agentic" and g in native_groups:
                continue
            role = "run_shaping" if "run_shaping" in by.values() else "exposed"
            for p in _package_closure(root, [f"data_sheets_schema.cli.{g}"]):
                s.add(_rel(root, p), approach, role if role == "exposed" else _module_role(p, derived), "live",
                      f"closure of the CLI group `d4d {g}` that {', '.join(sorted(by))} run", runs=False)

    # ---- deterministic arms: the commands that build a non-baseline arm's
    # bundle, and what they import (#4054)
    for p in det_closure:
        rel = _rel(root, p)
        why = (f"deterministic arm command ({arm_commands[rel]})" if rel in arm_commands
               else "import closure of the deterministic arm commands")
        s.add(rel, "deterministic", _module_role(p, derived), "live", why, runs=False)

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
                s.add(qrel, approach, role if role == "exposed" else _module_role(q, derived), "live",
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

    # ---- upstream input (listed, never gates); the text the data flow
    # carries into what a step writes is model text there, span by span
    # (#4085)
    for rel, why in shared.items():
        s.add(rel, "shared_input", "run_shaping", "live", "input acquisition / bundle shaping: " + why)

    # ---- text a model receives, by data flow (#4054, #4085), found above
    for rel, sp in spans.items():
        if rel in s.files:
            s.files[rel].text_spans = sp
    # reported where it changes something: a module no approach already
    # treats as model-facing as a whole
    facts["model_text"] = {rel: list(dict.fromkeys(label for *_, label in sp)) for rel, sp in sorted(spans.items())
                           if rel in s.files and "model_facing" not in s.files[rel].roles.values()}
    # the derivation of which package modules write model text, cross-checked
    # against the hand-kept list (#4085): a live module is one a generation
    # closure reaches
    live = {_package_module_name(p) for p in api_closure + native_closure + det_closure} - {None}
    facts["model_facing_modules"] = {
        "derived": {name: list(dict.fromkeys(labels))[:3] for name, labels in derived.items() if name in live},
        "derived_outside_closures": sorted(name for name in derived if name not in live),
        "listed": sorted(MODEL_FACING_MODULES),
        "derived_not_listed": sorted(name for name in derived if name in live and name not in MODEL_FACING_MODULES),
        "listed_not_derived": sorted(name for name in MODEL_FACING_MODULES if name not in derived)}
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
    # Both CLI routes enter here before classifying any surface (#4996).
    missing = ["ast." + name for name in
               ("Match", "MatchAs", "MatchStar", "MatchMapping", "match_case")
               if not hasattr(ast, name)]
    if missing:
        raise ConfigError(f"{_interpreter()} lacks required scanner AST capabilities: "
                          + ", ".join(missing) + "; use an interpreter with these capabilities "
                          "that can also parse the checkout (`poetry run python`) (#4996)")
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


def _early_axis_refusal(tree: ast.Module) -> dict:
    """A positive version-axis refusal at the first executable statement.

    This proves an API continuation has a false axis; it does not infer what
    an opaque native validator admits. Only a default-zero integer field and
    the literal ``getattr(spec, field, 0) or spec.render_version == N`` guard
    are supported. A reordered, weakened or rebound guard is not evidence.
    """
    fn = _function(tree, 'execute')
    if fn is None:
        raise _not_derived('early API axis refusal', 'missing execute')
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RunSpec'), None)
    fields = {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign)
              and isinstance(n.target, ast.Name) and isinstance(n.annotation, ast.Name)
              and n.annotation.id == 'int' and isinstance(n.value, ast.Constant)
              and type(n.value.value) is int and n.value.value == 0} if cls else set()
    candidates = [n for n in ast.walk(fn) if isinstance(n, ast.If)
        and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == 'getattr'
                and len(x.args) >= 2 and ast.unparse(x.args[0]) == 'spec'
                and isinstance(x.args[1], ast.Constant) and x.args[1].value in fields
                for x in ast.walk(n.test))
        and any(isinstance(x, ast.Raise) for x in ast.walk(n))]
    # Later ordinary optional dispatches may contain refusals. Only direct
    # raising guards claim an API boundary; the selected native guard must be
    # one of these, not a nested check reached after effects.
    candidates = [n for n in candidates if any(isinstance(x, ast.Raise) for x in n.body)]
    if not candidates:
        return {}
    body = fn.body[1:] if (isinstance(fn.body[0], ast.Expr)
        and isinstance(fn.body[0].value, ast.Constant) and type(fn.body[0].value.value) is str) else fn.body
    fail = lambda: _not_derived('early API axis refusal', 'unsupported guard, default, binding or statement order')
    if len(candidates) != 1 or candidates[0] is not body[0] or fn.decorator_list or 'getattr' in _params(fn):
        raise fail()
    guard = candidates[0]
    if sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'execute' for n in tree.body) != 1:
        raise fail()
    if guard.orelse or len(guard.body) != 1 or not isinstance(guard.body[0], ast.Raise):
        raise fail()
    if not isinstance(guard.test, ast.BoolOp) or not isinstance(guard.test.op, ast.Or) or len(guard.test.values) != 2:
        raise fail()
    call, compare = guard.test.values
    if not (isinstance(call, ast.Call) and len(call.args) == 3 and not call.keywords
            and isinstance(call.args[1], ast.Constant) and call.args[1].value in fields
            and isinstance(call.args[2], ast.Constant) and type(call.args[2].value) is int and call.args[2].value == 0
            and isinstance(compare, ast.Compare) and len(compare.ops) == 1
            and isinstance(compare.ops[0], ast.Eq) and ast.unparse(compare.left) == 'spec.render_version'
            and isinstance(compare.comparators[0], ast.Constant) and type(compare.comparators[0].value) is int):
        raise fail()
    field, renderer = call.args[1].value, compare.comparators[0].value
    expected = ast.parse(f"getattr(spec, {field!r}, 0) or spec.render_version == {renderer}", mode='eval').body
    if ast.dump(guard.test) != ast.dump(expected):
        raise fail()
    if any((isinstance(n, ast.Name) and n.id == 'getattr' and isinstance(n.ctx, (ast.Store, ast.Del)))
           or _rebinding(n, 'getattr', fn) for n in ast.walk(tree)):
        raise fail()
    return {'field': field, 'api_value': 0, 'renderer': renderer, 'line': guard.lineno}


def derive_native_shared_route(root: Path, tree: ast.Module) -> dict | None:
    """Source proof of a separate native render selector, not launch approval.

    Recognize the closed validator prefix and its actual RunSpec/CLI call
    sites. No generation module is imported. The remaining capture validators
    can narrow admission; they cannot be used to infer an API procedure or a
    successful controller execution.
    """
    field = 'native_shared_generation_version'
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RunSpec'), None)
    declarations = [n for n in cls.body if isinstance(n, ast.AnnAssign)
                    and isinstance(n.target, ast.Name) and n.target.id == field] if cls else []
    if not declarations:
        return None
    fail = lambda detail: _not_derived('separate native shared render route', detail)
    dump = lambda n: ast.dump(n, include_attributes=False)
    declaration = ast.parse(f'{field}: int = 0').body[0]
    if len(declarations) != 1 or dump(declarations[0]) != dump(declaration):
        raise fail('axis is not one default-zero integer declaration')
    early = _early_axis_refusal(tree)
    if not early or early['field'] != field:
        raise fail('missing proven early API refusal')
    relative = 'src/data_sheets_schema/native_shared_render.py'
    contract_path = 'src/data_sheets_schema/native_shared_contract.py'
    renderer_tree, contract = _tree(root / relative), _tree(root / contract_path)
    constants = {}
    for name, expected_type in (('RENDERER', int), ('CONDITION', str), ('RUNTIME', str), ('VERSION', int)):
        bindings = [n for n in contract.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if len(bindings) != 1 or not isinstance(bindings[0].value, ast.Constant) or type(bindings[0].value.value) is not expected_type:
            raise fail('contract constants lack unique typed literal bindings')
        binding = bindings[0]
        if any((isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del))
                and n is not binding.targets[0]) or isinstance(n, ast.arg) and n.arg == name
               or _rebinding(n, name, None) for n in ast.walk(contract)):
            raise fail('contract constant is rebound')
        constants[name] = binding.value.value
    if (constants['VERSION'] != 1 or constants['RENDERER'] != early['renderer']
            or constants['RENDERER'] not in derive_admitted_renderers(tree)):
        raise fail('validator contract and API refusal disagree')
    fn = _function(renderer_tree, 'validate_spec')
    if (fn is None or fn.decorator_list or ast.unparse(fn.args) != 'spec'
            or sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'validate_spec'
                   for n in renderer_tree.body) != 1):
        raise fail('unsupported validator signature or decorator')
    imports = [n for n in renderer_tree.body if isinstance(n, ast.ImportFrom) and n.level == 1
               and n.module is None and len(n.names) == 1 and n.names[0].name == 'native_shared_contract'
               and n.names[0].asname == 'c']
    if len(imports) != 1:
        raise fail('validator contract import is not exact')
    for name in ('c', 'getattr', 'type', 'int'):
        if any((isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del)))
               or _rebinding(n, name, fn) for n in ast.walk(renderer_tree)
               if n is not imports[0].names[0]):
            raise fail('validator authority or builtin is rebound')
    # Exception messages are diagnostics, not selector authority. Everything
    # else in these six statements is exact, including zero/default semantics.
    class RaisingShape(ast.NodeTransformer):
        def visit_Raise(self, node):
            return ast.Raise(exc=None, cause=None)
    def shape(nodes):
        return dump(RaisingShape().visit(ast.parse('\n'.join(ast.unparse(n) for n in nodes))))
    companions = ('native_source_attribution_version', 'shared_generation_version',
                  'api_playbook_version', 'receipt_completion_version', 'removal_repair_version')
    prefix = ast.parse(f'''version = getattr(spec, {field!r}, 0)
registration = getattr(spec, 'native_shared_generation_registration', None)
if type(version) is not int or version not in (0, 1):
    raise ValueError()
if not version:
    if registration is not None or spec.render_version == {constants['RENDERER']}:
        raise ValueError()
    return None
if (spec.condition != c.CONDITION or type(spec.render_version) is not int
        or spec.render_version != c.RENDERER or spec.runtime != c.RUNTIME
        or spec.method != 'claudecode_direct' or spec.out_dir is not None
        or spec.prompt_text_env is not True):
    raise ValueError()
for key in {companions!r}:
    if type(getattr(spec, key)) is not int or getattr(spec, key) != 0:
        raise ValueError()
''').body
    if shape(fn.body[:len(prefix)]) != shape(prefix):
        raise fail('unsupported delegated admission prefix')
    if any((isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del))
            and ast.unparse(n.value) == 'spec') or isinstance(n, ast.Name) and n.id == 'spec'
           and isinstance(n.ctx, (ast.Store, ast.Del)) or _rebinding(n, 'spec', fn)
           or isinstance(n, ast.Call) and ast.unparse(n.func) in {'setattr', 'delattr'}
           or isinstance(n, ast.Call) and ast.unparse(n.func) != 'getattr'
              and (any(isinstance(x, ast.Name) and x.id == 'spec' for x in n.args)
                   or isinstance(n.func, ast.Attribute) and ast.unparse(n.func.value) == 'spec')
           for n in ast.walk(fn)):
        raise fail('delegated selector mutates its spec')
    init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__post_init__'), None)
    expected_import = ast.parse('from .native_shared_render import validate_spec as validate_native_shared').body[0]
    expected_call = ast.parse('validate_native_shared(self)').body[0]
    imports_at = [i for i, n in enumerate(init.body) if dump(n) == dump(expected_import)] if init else []
    if (len(imports_at) != 1 or imports_at[0] + 1 >= len(init.body)
            or dump(init.body[imports_at[0] + 1]) != dump(expected_call)):
        raise fail('RunSpec does not call the exact validator directly')
    if any(isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom)) for n in ast.walk(init)):
        raise fail('RunSpec can exit before completing selector validation')
    allowed_alias = init.body[imports_at[0]].names[0]
    if any((isinstance(n, ast.Name) and n.id == 'validate_native_shared' and isinstance(n.ctx, (ast.Store, ast.Del)))
           or _rebinding(n, 'validate_native_shared', init) for n in ast.walk(init) if n is not allowed_alias):
        raise fail('RunSpec validator is rebound')
    guard_test = ast.parse(f"getattr(spec, {field!r}, 0) or spec.render_version == {constants['RENDERER']}", mode='eval').body
    evidence = [f'{RUNNER}:{declarations[0].lineno}', f'{RUNNER}:{early["line"]}',
                f'{RUNNER}:{init.body[imports_at[0]+1].lineno}', f'{relative}:{fn.lineno}']
    for name in ('resolve_prompt', 'build_phase'):
        caller = _function(tree, name)
        body = caller.body if caller else []
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and type(body[0].value.value) is str:
            body = body[1:]
        guard = body[0] if body else None
        if not isinstance(guard, ast.If) or dump(guard.test) != dump(guard_test) or guard.orelse:
            raise fail('prompt/phase route is not an early exact guarded branch')
        expected = ast.parse('from .native_shared_render import instruction\nreturn instruction(spec)').body
        if name == 'resolve_prompt':
            if [dump(n) for n in guard.body] != [dump(n) for n in expected]:
                raise fail('selected instruction delegates another spec or builder')
        elif len(guard.body) != 1 or not isinstance(guard.body[0], ast.Raise):
            raise fail('API phase builder does not refuse the selected native route')
        evidence.append(f'{RUNNER}:{guard.lineno}')

    cli_path = 'src/data_sheets_schema/cli/prompt.py'
    cli = _tree(root / cli_path)
    command = _function(cli, 'render_native_shared')
    if command is None or sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                              and n.name == 'render_native_shared' for n in cli.body) != 1:
        raise fail('missing offline render CLI consumer')
    command_decorators = [n for n in command.decorator_list if isinstance(n, ast.Call)
                          and ast.unparse(n.func) == 'prompt.command']
    if (len(command_decorators) != 1 or command_decorators[0].keywords
            or [ast.unparse(n) for n in command_decorators[0].args] != [repr('render-native-shared')]):
        raise fail('offline CLI command spelling is not derived')
    expected_imports = ast.parse('''from data_sheets_schema.api_runner import RunSpec
from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema.native_shared_selection import capture
from data_sheets_schema.native_shared_controller import bind_runtime
''').body
    for imp in expected_imports:
        matches = [n for n in command.body if dump(n) == dump(imp)]
        if len(matches) != 1:
            raise fail('CLI uses an unproved constructor, contract or runtime binding')
        alias = matches[0].names[0]
        name = alias.asname or alias.name
        if any((isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del)))
               or _rebinding(n, name, command) for n in ast.walk(command) if n is not alias):
            raise fail('CLI selected binding is rebound')
    tries = [n for n in command.body if isinstance(n, ast.Try)]
    if len(tries) != 1:
        raise fail('unsupported offline CLI structure')
    statements = tries[0].body
    capture_prefix = ast.parse("captured = capture(selection)\ndocument = captured.document()\ninputs = document['inputs']").body
    if [dump(n) for n in statements[:3]] != [dump(n) for n in capture_prefix]:
        raise fail('CLI does not capture its actual selection argument')
    assignments = [(i, n) for i, n in enumerate(statements) if isinstance(n, ast.Assign)
                   and len(n.targets) == 1 and ast.unparse(n.targets[0]) == 'spec']
    if len(assignments) != 1:
        raise fail('CLI lacks one selected spec')
    index, assignment = assignments[0]
    call = assignment.value
    if not isinstance(call, ast.Call) or ast.unparse(call.func) != 'RunSpec' or call.args:
        raise fail('CLI spec constructor is not proven')
    keywords = {k.arg: k.value for k in call.keywords}
    required = {'condition': 'contract.CONDITION', 'render_version': 'contract.RENDERER',
                'runtime': 'contract.RUNTIME', field: '1', 'prompt_text_env': 'True'}
    if len(keywords) != len(call.keywords) or any(k not in keywords or ast.unparse(keywords[k]) != v for k,v in required.items()):
        raise fail('CLI native identity differs from the contract')
    tail = ast.parse('bind_runtime(spec, runtime_declaration, max_draft_checks)\ntext = spec.instruction').body
    if [dump(n) for n in statements[index+1:index+3]] != [dump(n) for n in tail]:
        raise fail('CLI does not bind the explicit runtime before rendering the same spec')
    # The consumer is render-only. A new call here is not silently relabeled an
    # execution gate; its source shape needs a separate derivation/review.
    allowed_calls = {'capture', 'captured.document', 'ValueError', 'RunSpec', 'Path',
        'captured.registration.raw.decode', 'run_date.strftime', 'bind_runtime',
        'Path(out).resolve', 'destination.open', 'stream.write', 'click.ClickException',
        'str', 'text.encode', 'click.echo', 'hashlib.sha256', 'hashlib.sha256(raw).hexdigest', 'len'}
    if any(ast.unparse(n.func) not in allowed_calls for statement in command.body
           for n in ast.walk(statement) if isinstance(n, ast.Call)):
        raise fail('offline render consumer contains an unsupported call')
    evidence.append(f'{cli_path}:{command.lineno}')
    binder = 'src/data_sheets_schema/native_shared_controller.py'
    binder_present = (root / binder).is_file()
    if binder_present:
        _tree(root / binder)  # a present but unreadable/unparsed module is not coverage
    return {'field': field, 'default': 0, 'enabled_values': [constants['VERSION']],
            'condition': constants['CONDITION'], 'renderer': constants['RENDERER'],
            'runtime': constants['RUNTIME'], 'companion_axes': dict.fromkeys(companions, 0),
            'api_execute': 'refused before dry-run, locks or dispatch',
            'api_phase_builder': 'refused', 'instruction_builder': relative + ':instruction',
            'cli': 'd4d prompt render-native-shared',
            'runtime_binding': {'path': binder, 'source_present': binder_present,
                'basis': 'Source presence only; the binder is not executed or its acceptance inferred.'
                if binder_present else 'Referenced binder source is absent in this snapshot; runnable rendering is not established.'},
            'scope': 'Offline rendering of the explicit native selection and runtime declaration; '
                     'separate execution registration and controller acceptance are not established by this scan.',
            'model_calls_minimum': None, 'evidence': evidence}


def derive_native_shared_procedure(root: Path) -> dict:
    """Read the selected response roster, not native execution/acceptance.

    This deliberately recognizes a few concrete producer shapes. Phase,
    correction and terminal obligations are source-linked descriptions below,
    not another implementation of their runtime validators.
    """
    prefix = 'src/data_sheets_schema/'
    paths = {name: prefix + name + '.py' for name in (
        'native_shared_stage', 'native_shared_receipts', 'typed_audit',
        'audit_omissions', 'native_shared_render')}
    trees = {name: _tree(root / path) for name, path in paths.items()}
    fail = lambda detail: _not_derived('native shared response roster', detail)
    dump = lambda node: ast.dump(node, include_attributes=False)
    same = lambda node, text: dump(node) == dump(ast.parse(text).body[0])

    def function(module, name, owner=None):
        body = trees[module].body
        if owner:
            classes = [n for n in body if isinstance(n, ast.ClassDef) and n.name == owner]
            if len(classes) != 1:
                raise fail('missing unique ' + owner)
            if any((isinstance(n, ast.Name) and n.id == owner and isinstance(n.ctx, (ast.Store, ast.Del)))
                   or (isinstance(n, ast.Attribute) and ast.unparse(n) == owner + '.' + name
                       and isinstance(n.ctx, (ast.Store, ast.Del))) for n in ast.walk(trees[module])):
                raise fail('fixed producer class/method is replaced: ' + owner + '.' + name)
            body = classes[0].body
        found = [n for n in body if isinstance(n, ast.FunctionDef) and n.name == name]
        if len(found) != 1 or found[0].decorator_list:
            raise fail('unsupported producer ' + name)
        if owner is None and any((isinstance(n, ast.Name) and n.id == name
                                  and isinstance(n.ctx, (ast.Store, ast.Del)))
                                 or (isinstance(n, ast.alias) and (n.asname or n.name) == name)
                                 or (isinstance(n, ast.arg) and n.arg == name)
                                 for n in ast.walk(trees[module])):
            raise fail('producer binding is replaced or shadowed: ' + name)
        return found[0]

    def statement(fn, text):
        found = [n for n in fn.body if same(n, text)]
        if len(found) != 1:
            raise fail('unsupported ' + fn.name + ' producer: ' + text.splitlines()[0])
        return found[0]

    def assignment(fn, target):
        found = [n for n in fn.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and ast.unparse(n.targets[0]) == target]
        if len(found) != 1:
            raise fail('missing unique ' + target + ' binding in ' + fn.name)
        return found[0]

    def fixed_import(module, source, name, alias):
        tree = trees[module]
        expected = ast.parse(f'from .{source} import {name} as {alias}' if source else
                             f'from . import {name} as {alias}').body[0]
        found = [n for n in tree.body if dump(n) == dump(expected)]
        if len(found) != 1:
            raise fail('missing fixed producer import ' + alias)
        binding = found[0].names[0]
        if any((isinstance(n, ast.Name) and n.id == alias and isinstance(n.ctx, (ast.Store, ast.Del)))
               or (isinstance(n, ast.alias) and n is not binding and (n.asname or n.name) == alias)
               or (isinstance(n, ast.arg) and n.arg == alias) for n in ast.walk(tree)):
            raise fail('producer import is shadowed: ' + alias)

    def field(value, name):
        if not isinstance(value, ast.Dict):
            raise fail('producer does not return a literal mapping')
        if any(not isinstance(key, ast.Constant) or type(key.value) is not str for key in value.keys):
            raise fail('counted authority mapping has unpacked or dynamic keys')
        keys = [key.value for key in value.keys]
        if len(keys) != len(set(keys)):
            raise fail('counted authority mapping has duplicate keys')
        found = [v for k, v in zip(value.keys, value.values)
                 if isinstance(k, ast.Constant) and k.value == name]
        if len(found) != 1:
            raise fail('missing unique payload field ' + name)
        return found[0]

    def unchanged(fn, name, allowed, *, after=None):
        """Only the matched producer/consumer nodes may use this value.

        This is a closed local-use check, not an alias or control-flow engine.
        An extra read can hand a mutable value to an unknown helper, so it is
        unsupported just like an extra store or subscript/method mutation.
        """
        def selected(node):
            return isinstance(node, (ast.Name, ast.Attribute)) and ast.unparse(node) == name
        permitted = {id(n) for tree in allowed for n in ast.walk(tree) if selected(n)}
        region = [fn] if after is None else fn.body[fn.body.index(after):]
        nodes = [n for tree in region for n in ast.walk(tree)]
        actual = {id(n) for n in nodes if selected(n)}
        if actual != permitted or (name.isidentifier() and any(
                _rebinding(n, name, fn) for n in nodes)):
            raise fail(fn.name + ' changes or escapes counted ' + name)

    def body(fn):
        return [n for n in fn.body if not (isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]

    def exact_body(fn, text):
        expected = ast.parse('def expected():\n    ' + text).body[0].body
        if [dump(n) for n in body(fn)] != [dump(n) for n in expected]:
            raise fail('unsupported fixed delegation in ' + fn.name)

    def sole_return(fn, expected):
        if [n for n in ast.walk(fn) if isinstance(n, ast.Return)] != [expected]:
            raise fail('alternate counted result in ' + fn.name)

    fixed_import('native_shared_stage', '', 'native_shared_receipts', 'nr')
    fixed_import('native_shared_stage', '', 'typed_audit', 'typed')
    fixed_import('native_shared_stage', '', 'native_catalog_reuse', 'catalog_reuse')
    # typed_audit's existing grouped import is intentionally read as a binding,
    # rather than imposing a new import layout on that producer.
    for module, name, alias in (('typed_audit', 'audit_batches', 'batches'),
                                ('typed_audit', 'audit_omissions', 'omissions')):
        tree = trees[module]
        bindings = [a for n in tree.body if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module is None
                    for a in n.names if a.name == name and a.asname == alias]
        if len(bindings) != 1 or any(isinstance(n, ast.Name) and n.id == alias
                                   and isinstance(n.ctx, (ast.Store, ast.Del)) for n in ast.walk(tree)):
            raise fail('missing fixed typed producer ' + alias)

    run = function('native_shared_stage', 'run', '_Replay')
    requested = statement(run, "requested = nr._prepare(self.s, self.e, self.p, self.catalogs)['requested_paths']")
    branches = [n for n in run.body if isinstance(n, ast.If) and ast.unparse(n.test) == 'requested']
    if len(branches) != 1:
        raise fail('receipt work lacks its exact positive conditional')
    branch = branches[0]
    expected = ast.parse("if not self._stage(c.StageCursor(ordinal=ordinal, kind='receipt', target_id='receipt')):\n    return self\nordinal += 1").body
    if [dump(n) for n in branch.body] != [dump(n) for n in expected]:
        raise fail('receipt is not one conditional response-bearing stage')
    if not branch.orelse or not same(branch.orelse[0],
            'self.receipt = nr._complete(self.s, self.e, self.p, None, self.catalogs)'):
        raise fail('zero-work receipt does not complete without an answer')
    stages = [n for n in ast.walk(run) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'self._stage']
    if len(stages) != 2 or sum(isinstance(n, ast.Name) and n.id == 'requested' for n in ast.walk(run)) != 2:
        raise fail('unsupported extra stage or receipt-condition use')
    receipt_fn = function('native_shared_receipts', '_prepare')
    receipt_paths = statement(receipt_fn, 'paths = receipts.uncovered_receiptable_leaves(receipt, manifest, texts, full, md5, original=full, identifier_bases=bases)')
    returns = [n for n in receipt_fn.body if isinstance(n, ast.Return)]
    if len(returns) != 1 or ast.unparse(field(returns[0].value, 'requested_paths')) != 'paths':
        raise fail('receipt condition is not the uncovered-leaf result')
    unchanged(receipt_fn, 'paths', [receipt_paths.targets[0], field(returns[0].value, 'requested_paths')])
    sole_return(receipt_fn, returns[0])

    packet_fn = function('native_shared_stage', '_packet', '_Replay')
    packet_assignment = assignment(packet_fn, 'packet')
    packet_call = packet_assignment.value
    if not isinstance(packet_call, ast.Call) or ast.unparse(packet_call.func) != 'typed._prepare' or packet_call.args:
        raise fail('native worker packet is not the fixed typed preparation')
    kwargs = {k.arg: ast.unparse(k.value) for k in packet_call.keywords}
    if kwargs.get('_catalog_lookup') != 'catalog_reuse._CatalogLookup(self.catalogs, self.s)':
        raise fail('native packet lacks its fixed private receipt-catalog association')
    for key, value in {'original_full': 'self.p.full.raw', 'max_paths': "limits['max_paths_per_worker']",
                       'max_inventory_bytes': "limits['max_inventory_bytes']", 'max_workers': "limits['max_workers']"}.items():
        if kwargs.get(key) != value:
            raise fail('worker plan does not use the original record and selected partition limits')
    packet_bound = statement(packet_fn, "if len(packet['plan']['inventory']['values']) > limits['max_populated_paths']:\n    raise ValueError('native global populated path bound exceeded')")
    packet_return = statement(packet_fn, 'return packet')
    unchanged(packet_fn, 'packet', [packet_assignment.targets[0], packet_bound, packet_return])
    sole_return(packet_fn, packet_return)

    # The public producer must actually reach the inspected fresh derivation.
    # The cache branch below recognizes only its fixed product transport; it
    # does not reproduce cache limits, key security or runtime validation.
    exact_body(function('typed_audit', 'prepare'), '''return _prepare(
        protocol=protocol, original_full=original_full, bundle=bundle, manifest=manifest,
        receipt=receipt, context=context, schema_path=schema_path,
        max_output_tokens=max_output_tokens, original_core=original_core,
        source_manifest=source_manifest, project=project, max_request_bytes=max_request_bytes,
        max_paths=max_paths, max_inventory_bytes=max_inventory_bytes, max_workers=max_workers,
        schema_snapshot=schema_snapshot, derivations=derivations, captured_assets=captured_assets)''')
    prepare = function('typed_audit', '_prepare')
    inputs = statement(prepare, '''inputs = {key: _blob(value) for key, value in dict(
        original_full=original_full, bundle=bundle, manifest=manifest, receipt=receipt,
        context=context, original_core=original_core, source_manifest=source_manifest).items()
        if value is not None}''')
    limits = statement(prepare, '''limits = dict(max_output_tokens=max_output_tokens,
        max_request_bytes=max_request_bytes, max_paths=max_paths,
        max_inventory_bytes=max_inventory_bytes, max_workers=max_workers)''')
    derive_call = statement(prepare, 'derived, _, _ = _derive(inputs, rows, project, limits, derivations=derivations, captured_assets=captured_assets, _schema_reuse=_schema_reuse)')
    seal = statement(prepare, '''packet = _seal(dict(kind=PACKET,
        protocol=audit_protocol.select(protocol), inputs=inputs, schema_sources=rows,
        project=project, limits=limits, **derived, limitations=list(LIMITATIONS)))''')
    packet_size = statement(prepare, '_bounded_json(_json(packet), "packet", MAX_PACKET_BYTES)')
    packet_validation = statement(prepare, '''for worker in packet['plan']['workers']:
        worker_request(packet, worker['id'], derivations=derivations, captured_assets=captured_assets)''')
    returned = statement(prepare, 'return packet')
    sole_return(prepare, returned)
    for name, uses in (('inputs', [inputs.targets[0], derive_call, seal]),
                       ('limits', [limits.targets[0], derive_call, seal]),
                       ('derived', [derive_call.targets[0], seal]),
                       ('packet', [seal.targets[0], packet_size, packet_validation, returned])):
        unchanged(prepare, name, uses)
    if not (prepare.body.index(inputs) < prepare.body.index(derive_call)
            and prepare.body.index(limits) < prepare.body.index(derive_call)
            < prepare.body.index(seal) < prepare.body.index(packet_size)
            < prepare.body.index(packet_validation) < prepare.body.index(returned)):
        raise fail('typed preparation does not preserve producer/return order')
    exact_body(function('typed_audit', '_seal'), 'return {**value, "sha256": _sha(_json(value))}')

    dispatch = function('typed_audit', '_derive')
    exact_body(dispatch, '''if derivations is not None:
        if type(derivations) is not DerivationCache:
            raise ValueError('derivations must be an explicit DerivationCache')
        return derivations._derive(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)
    if captured_assets is None:
        return _derive_uncached(inputs, schema_rows, project, limits)
    if _schema_reuse is not None:
        return _derive_uncached(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)
    return _derive_uncached(inputs, schema_rows, project, limits, captured_assets=captured_assets)''')
    cache_init = function('typed_audit', '__init__', 'DerivationCache')
    empty = statement(cache_init, 'self._rows, self._bytes = {}, 0')
    unchanged(cache_init, 'self._rows', [empty.targets[0]])
    cache = function('typed_audit', '_derive', 'DerivationCache')
    lookup = statement(cache, 'encoded = self._rows.get(key)')
    misses = [n for n in cache.body if isinstance(n, ast.If) and ast.unparse(n.test) == 'encoded is None']
    if len(misses) != 1:
        raise fail('cache producer lacks its unique miss branch')
    miss = misses[0]
    expected_miss = ast.parse('''if encoded is None:
        derived, raw, prepared = _derive(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)
        encoded = _json({'derived': derived, 'raw': {name: _blob(value) for name, value in raw.items()},
                         'prepared_payload_json': prepared.payload_json})
        if len(encoded) <= self.max_bytes:
            while self._rows and (len(self._rows) >= self.max_entries or self._bytes + len(encoded) > self.max_bytes):
                self._bytes -= len(self._rows.pop(next(iter(self._rows))))
            self._rows[key] = encoded
            self._bytes += len(encoded)''').body[0]
    if dump(miss) != dump(expected_miss):
        raise fail('cache miss does not transport the complete fixed derivation')
    decoded = statement(cache, 'value = json.loads(encoded)')
    cache_return = statement(cache, '''return value['derived'], {
        name: _unblob(blob) for name, blob in value['raw'].items()}, omissions.Prepared(value['prepared_payload_json'])''')
    sole_return(cache, cache_return)
    for name, uses in (('encoded', [lookup, miss, decoded]),
                       ('value', [miss.body[1], decoded, cache_return]),
                       ('derived', [miss.body[0], miss.body[1]]),
                       ('self._rows', [lookup, miss])):
        unchanged(cache, name, uses, after=None if name == 'self._rows' else lookup)
    if not (cache.body.index(lookup) < cache.body.index(miss)
            < cache.body.index(decoded) < cache.body.index(cache_return)):
        raise fail('cache product lookup/producer/return order changed')
    derived = function('typed_audit', '_derive_uncached')
    plan = assignment(derived, 'plan')
    if not same(plan, "plan = batches.make_plan(raw['original_full'].decode('utf-8'), version=2, **{k: limits[k] for k in ('max_paths', 'max_inventory_bytes', 'max_workers')})"):
        raise fail('typed plan is not derived from the original full and partition limits')
    prepared = assignment(derived, 'prepared').value
    if not isinstance(prepared, ast.Call) or ast.unparse(prepared.func) != 'omissions._prepare':
        raise fail('typed omission request does not use its actual constructor')
    statement(derived, '''prepared = omissions._prepare(record=raw['original_full'], bundle=raw['bundle'],
        manifest=raw['manifest'], receipt=raw['receipt'], context=raw['context'],
        schema_path=snapshot.sources[0][1], schema_snapshot=snapshot,
        max_output_tokens=limits['max_output_tokens'], max_request_bytes=limits['max_request_bytes'],
        captured_assets=captured_assets, _catalog=(_schema_reuse.for_snapshot(snapshot)
            if captured_assets is not None and type(_schema_reuse) is _SchemaReuse else None))''')
    result = [n for n in derived.body if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple)]
    if len(result) != 1 or ast.unparse(field(result[0].value.elts[0], 'plan')) != 'plan' or \
            ast.unparse(field(result[0].value.elts[0], 'omission_request')) != 'prepared.request()':
        raise fail('typed result replaces its worker plan or omission request')
    sole_return(derived, result[0])
    worker_payloads = statement(derived, '''workers = {worker['id']: _json({
        'stage': 'worker', 'shared_context_sha256': _sha(shared.encode()),
        'plan_sha256': plan['sha256'], 'assignment': worker, 'inventory': plan['inventory'],
        'output_contract': contracts['worker']}).decode('utf-8') for worker in plan['workers']}''')
    unchanged(derived, 'plan', [plan.targets[0], worker_payloads, field(result[0].value.elts[0], 'plan')])
    shared = assignment(derived, 'shared').value
    if not (isinstance(shared, ast.Call) and isinstance(shared.func, ast.Attribute)
            and isinstance(shared.func.value, ast.Call) and ast.unparse(shared.func.value.func) == '_json'
            and len(shared.func.value.args) == 1):
        raise fail('typed shared context lacks the fixed payload')
    shared_fields = shared.func.value.args[0]
    prepared_reads = [field(shared_fields, key) for key in ('context', 'schema')]
    if [ast.unparse(n) for n in prepared_reads] != [
            "prepared.request()['payload']['context']", "prepared.request()['payload']['schema']"]:
        raise fail('typed context does not read its actual omission request')
    unchanged(derived, 'prepared', [assignment(derived, 'prepared').targets[0], *prepared_reads,
        field(result[0].value.elts[0], 'omission_request'), result[0].value.elts[2]])

    packet_binding = statement(run, 'self.packet = self._packet()')
    workers = statement(run, "roster = [('worker', worker['id']) for worker in self.packet['plan']['workers']]")
    unchanged(run, 'self.packet', [packet_binding.targets[0], workers])
    fixed = statement(run, "roster += [('omission', 'omission'), ('integration', 'integration')]")
    loops = [n for n in run.body if isinstance(n, ast.For) and ast.unparse(n.iter) == 'roster']
    loop_text = 'for kind, target in roster:\n    if not self._stage(c.StageCursor(ordinal=ordinal, kind=kind, target_id=target)):\n        return self\n    ordinal += 1'
    if len(loops) != 1 or not same(loops[0], loop_text):
        raise fail('required worker/omission/integration roster is not fully iterated')
    bound = statement(run, "if ordinal - 1 + len(roster) > self.s.bounds()['max_submissions']:\n    raise ValueError('complete native stage roster exceeds declared submissions; no truncation')")
    if not (run.body.index(requested) < run.body.index(branch) < run.body.index(packet_binding)
            < run.body.index(workers) < run.body.index(fixed) < run.body.index(bound) < run.body.index(loops[0])):
        raise fail('required response roster order changed')
    if sum(isinstance(n, ast.Name) and n.id == 'roster' for n in ast.walk(run)) != 4:
        raise fail('required roster is filtered, extended or otherwise reused')

    # Public and typed callers reach the same fixed chunk/request constructor.
    # The private catalog handoff does not establish runtime schema validity.
    exact_body(function('audit_omissions', 'prepare'), '''return _prepare(
        record=record, bundle=bundle, manifest=manifest, receipt=receipt,
        context=context, schema_path=schema_path, max_output_tokens=max_output_tokens,
        schema_snapshot=schema_snapshot, max_request_bytes=max_request_bytes,
        captured_assets=captured_assets)''')
    omission = function('audit_omissions', '_prepare')
    chunk_calls = [n for n in ast.walk(omission) if isinstance(n, ast.Assign) and
                   same(n, 'chunks, _pins = evidence.source_chunks_from_bytes(bundle, manifest)')]
    if len(chunk_calls) != 1:
        raise fail('omission chunks are not the canonical captured bundle/manifest chunks')
    payload = assignment(omission, 'payload')
    chunk_list = field(payload.value, 'chunks')
    expected_chunks = ast.parse("[{'chunk': key, **value, 'prior_receipt_status': prior.get(key, 'unreviewed')} for key, value in chunks.items()]", mode='eval').body
    if dump(chunk_list) != dump(expected_chunks):
        raise fail('omission payload filters or replaces canonical chunks')
    stores = [n for n in ast.walk(omission) if isinstance(n, ast.Name) and n.id == 'chunks' and isinstance(n.ctx, (ast.Store, ast.Del))]
    if len(stores) != 1 or any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                              and ast.unparse(n.func.value) == 'chunks' and n.func.attr != 'items' for n in ast.walk(omission)):
        raise fail('canonical chunk map is modified before omission enumeration')
    encoded_payload = statement(omission, 'encoded = _json(payload)')
    omission_bound = statement(omission, '''if len(_json(Prepared(encoded).request()).encode()) > max_request_bytes:
        raise ValueError('complete request exceeds max_request_bytes; no partial request returned')''')
    omission_return = statement(omission, 'return Prepared(encoded)')
    sole_return(omission, omission_return)
    unchanged(omission, 'payload', [payload.targets[0], encoded_payload])
    unchanged(omission, 'encoded', [encoded_payload.targets[0], omission_bound, omission_return])
    if not (omission.body.index(payload) < omission.body.index(encoded_payload)
            < omission.body.index(omission_bound) < omission.body.index(omission_return)):
        raise fail('omission payload does not reach its captured return')
    exact_body(function('audit_omissions', 'request', 'Prepared'), '''payload = json.loads(self.payload_json)
    return {'format': FORMAT, 'request_sha256': _sha(self.payload_json.encode()),
            'payload': payload, 'limitations': list(LIMITATIONS)}''')

    commands = function('native_shared_render', 'commands')
    mapping = assignment(commands, 'result')
    if not isinstance(mapping.value, ast.Dict) or any(not isinstance(k, ast.Constant) or type(k.value) is not str
                                                     for k in mapping.value.keys):
        raise fail('helper kinds are not a literal command mapping')
    keys = [k.value for k in mapping.value.keys]
    extra = [n for n in commands.body if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Subscript) and ast.unparse(n.targets[0].value) == 'result']
    for node in extra:
        key = node.targets[0].slice
        if not isinstance(key, ast.Constant) or type(key.value) is not str:
            raise fail('helper key is dynamic')
        keys.append(key.value)
    statement(commands, 'return result')
    if len(keys) != len(set(keys)) or sum(isinstance(n, ast.Name) and n.id == 'result' for n in ast.walk(commands)) != 2 + len(extra):
        raise fail('helper mapping is mutated or has duplicate kinds')

    evidence = [f'{paths[module]}:{node.lineno}' for module, node in (
        ('native_shared_stage', run), ('native_shared_stage', packet_fn),
        ('native_shared_receipts', receipt_fn), ('typed_audit', derived),
        ('audit_omissions', omission), ('native_shared_render', commands))]
    return {'basis': 'Source-derived required response-bearing roster; no observed execution or enforcement proof.',
        'stages': [{'kind': 'receipt', 'cardinality': 'R = 0 or 1', 'condition': 'captured uncovered receiptable leaves; verified zero-work has no answer'},
                   {'kind': 'worker', 'cardinality': 'W, unknown until the original record is partitioned', 'requirement': 'every worker in the complete derived plan'},
                   {'kind': 'omission', 'cardinality': '1', 'requirement': 'all canonical chunks, including prior negative/redundant chunks'},
                   {'kind': 'integration', 'cardinality': '1', 'requirement': 'after all workers and omission'}],
        'protocol_responses': {'formula': 'R + W + 2', 'minimum': None, 'actual_count': None,
                               'unit': 'required response-bearing stage roster, not model calls or observed answers'},
        'helper_commands': keys, 'helper_kind_count': len(keys),
        'model_calls_minimum': None, 'evidence': evidence,
        'procedure_notes': [
            {'description': 'The selected renderer describes initial validation/sealing, genuine core derivation, reconciliation after checked assembly, final validations, report draft and recorder-last. These are runtime obligations, not scanner-verified execution.',
             'source': paths['native_shared_render'] + ':instruction'},
            {'description': 'The phase observer owns ordered helper and protected-artifact admission; this scanner does not duplicate those checks.',
             'source': prefix + 'native_shared_phase.py:PhaseState'},
            {'description': 'Report correction uses the explicit execution.max_draft_checks allowance. Actual checks and report rewrite count are unknown; a check allowance is not a rewrite count.',
             'source': prefix + 'native_shared_attribution.py:_Attribution'},
            {'description': 'Final gates and saved reconstruction remain separate acceptance obligations; helper kinds and source presence do not establish completion.',
             'source': prefix + 'native_shared_gates.py:check'}]}


def derive_execute_refusal(tree: ast.Module, admitted: list[int]) -> dict:
    """The renderers `api_runner.execute` refuses before it runs anything: a
    raising `render_version in (...)` or `>= N` test in its body (#4055). No
    such test is an empty refusal, reported as such."""
    fn = _function(tree, "execute")
    if fn is None:
        raise _not_derived("what api_runner.execute refuses", "api_runner.py defines no execute()")
    early = _early_axis_refusal(tree)
    refused, line = ({early['renderer']}, early['line']) if early else (set(), None)
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
      refuses its ordinary audit request, and `api_runner.execute` refuses
      what it lists. Selected helper replacements are derived separately."""
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
    api_path += (f"; `build_phase` refuses its ordinary audit request at renderer >= {floor}; "
                 "that builder call stops rather than dispatching a native agent")
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
                elif not found and isinstance(consts.get(expr.id), str):
                    # Imported helpers can name their phase in a module literal.
                    values.add(consts[expr.id])
                    found = True
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


def _optional_condition_scope(tree, init, field: str, validated: set[int]) -> tuple:
    """Read only a direct positive opt-in's raising condition-set refusal.

    A named set must be one literal module binding, used only for membership.
    Aliases, mutation, shadowing and control flow we cannot prove fail closed.
    Other calls in the opt-in block (e.g. registration validation) are not
    interpreted as condition declarations.
    """
    fail = lambda: _not_derived("which conditions make a follow-up turn",
                               f"unreadable condition restriction for optional gate `spec.{field}`")
    attr = lambda n, name: isinstance(n, ast.Attribute) and ast.unparse(n) == f"self.{name}"
    if any(isinstance(n, (ast.Raise, ast.Assert)) for n in init.body) or any(
           (isinstance(n, ast.Name) and n.id == "self" and isinstance(n.ctx, (ast.Store, ast.Del)))
           or _rebinding(n, "self", init)
           or (attr(n, "condition") and isinstance(n.ctx, (ast.Store, ast.Del))) for n in ast.walk(init)):
        raise fail()
    scopes, evidence = [], []
    parents = _parents(tree)
    for block in ast.walk(init):
        if not isinstance(block, (ast.If, ast.IfExp, ast.While, ast.Match)):
            continue
        test = block.subject if isinstance(block, ast.Match) else block.test
        if id(block) in validated or not any(attr(n, field) for n in ast.walk(test)):
            continue
        if not (isinstance(block, ast.If) and block in init.body and attr(block.test, field)):
            raise fail()
        # The disabled branch may validate companion options, but cannot carry
        # the enabled option's condition restriction.
        if any(_mentions_condition(n) for n in block.orelse):
            raise fail()
        for guard in block.body:
            if not isinstance(guard, ast.If):
                if _mentions_condition(guard) or any(isinstance(n, (ast.IfExp, ast.While, ast.For,
                        ast.Try, ast.With, ast.Match, ast.Raise, ast.Assert,
                        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                        for n in ast.walk(guard)):
                    raise fail()
                continue
            test = guard.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.NotIn) and attr(test.left, "condition")
                    and isinstance(test.comparators[0], ast.Name) and not guard.orelse
                    and len(guard.body) == 1 and isinstance(guard.body[0], ast.Raise)):
                raise fail()
            name = test.comparators[0].id
            declarations = [n for n in tree.body if
                (isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
                or (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == name)]
            if len(declarations) != 1:
                raise fail()
            declaration = declarations[0]
            value = declaration.value
            if isinstance(value, ast.Call):
                if not (isinstance(value.func, ast.Name) and value.func.id in {"frozenset", "set", "tuple"}
                        and len(value.args) == 1 and not value.keywords):
                    raise fail()
                if any((isinstance(n, ast.Name) and n.id == value.func.id
                        and isinstance(n.ctx, (ast.Store, ast.Del))) or _rebinding(n, value.func.id, init)
                       for n in ast.walk(tree)):
                    raise fail()
                value = value.args[0]
            if not isinstance(value, (ast.Tuple, ast.List, ast.Set)) or not value.elts or any(
                    not isinstance(n, ast.Constant) or type(n.value) is not str or not n.value.strip() for n in value.elts):
                raise fail()
            target = declaration.targets[0] if isinstance(declaration, ast.Assign) else declaration.target
            for node in ast.walk(tree):
                if _rebinding(node, name, init) or (isinstance(node, ast.arg) and node.arg == name):
                    raise fail()
                if not isinstance(node, ast.Name) or node.id != name or node is target:
                    continue
                parent = parents.get(id(node))
                if not (isinstance(node.ctx, ast.Load) and isinstance(parent, ast.Compare)
                        and len(parent.ops) == 1 and isinstance(parent.ops[0], (ast.In, ast.NotIn))
                        and node is parent.comparators[0]):
                    raise fail()
            scopes.append({n.value for n in value.elts})
            evidence.extend((declaration.lineno, block.lineno, guard.lineno))
    if not scopes:
        return None, []
    # Several direct refusals constrain the option by their intersection.
    scope = set.intersection(*scopes)
    if not scope:
        raise fail()
    return sorted(scope), sorted(set(evidence))


def _simple_optional_turn_selection(tree: ast.Module, test) -> dict:
    """A narrow, validated opt-in RunSpec axis, never an unknown truthy gate.

    Read the default, finite integer domain and API/renderer restriction from
    unconditional raising guards in __post_init__. New shapes fail closed.
    """
    fail = lambda: _not_derived("which conditions make a follow-up turn",
                               f"unvalidated optional gate `{ast.unparse(test)[:60]}`")
    if not (isinstance(test, ast.Attribute) and isinstance(test.value, ast.Name)
            and test.value.id == "spec"):
        raise fail()
    field = test.attr
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RunSpec"), None)
    if cls is None:
        raise fail()
    declarations = [n for n in cls.body if isinstance(n, ast.AnnAssign)
                    and isinstance(n.target, ast.Name) and n.target.id == field]
    init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__post_init__"), None)
    if (len(declarations) != 1 or init is None
            or not isinstance(declarations[0].annotation, ast.Name) or declarations[0].annotation.id != "int"
            or not isinstance(declarations[0].value, ast.Constant)
            or type(declarations[0].value.value) is not int or declarations[0].value.value != 0):
        raise fail()
    if any(isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del))
           and ast.unparse(n) == f"self.{field}" for n in ast.walk(init)):
        raise fail()
    if any(isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom)) for n in ast.walk(init)):
        raise fail()
    guards = [n for n in init.body if isinstance(n, ast.If) and len(n.body) == 1
              and isinstance(n.body[0], ast.Raise) and not n.orelse]
    dump = lambda n: ast.dump(n, include_attributes=False)
    domain, restrictions = [], []
    for guard in guards:
        for node in ast.walk(guard.test):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.NotIn)
                    and ast.unparse(node.left) == f"self.{field}"):
                continue
            try:
                values = ast.literal_eval(node.comparators[0])
            except (ValueError, TypeError):
                continue
            if (not isinstance(values, (tuple, list)) or not values or 0 not in values
                    or any(type(v) is not int or v < 0 for v in values) or not any(values)):
                continue
            expected = ast.parse(f"type(self.{field}) is not int or self.{field} not in {values!r}", mode="eval").body
            if dump(guard.test) == dump(expected):
                domain.append((sorted(set(values)), guard.lineno))
        for node in ast.walk(guard.test):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.NotEq)
                    and ast.unparse(node.left) == "self.render_version"
                    and isinstance(node.comparators[0], ast.Constant)
                    and type(node.comparators[0].value) is int):
                continue
            renderer = node.comparators[0].value
            expected = ast.parse(f"self.{field} and (self.is_agentic or self.render_version != {renderer})", mode="eval").body
            if dump(guard.test) == dump(expected):
                restrictions.append((renderer, guard.lineno))
    if len(domain) != 1 or len(restrictions) != 1:
        raise fail()
    admitted = derive_admitted_renderers(tree)
    if restrictions[0][0] not in admitted or restrictions[0][0] in derive_execute_refusal(tree, admitted)["refused"]:
        raise fail()
    conditions, condition_evidence = _optional_condition_scope(tree, init, field,
        {id(n) for n in guards if n.lineno in (domain[0][1], restrictions[0][1])})
    return {"field": field, "default": 0, "enabled_values": [v for v in domain[0][0] if v],
            "runtime": "api", "renderers": [restrictions[0][0]],
            **({"conditions": conditions} if conditions is not None else {}),
            "evidence": [f"api_runner.py:{n}" for n in
                         (declarations[0].lineno, domain[0][1], restrictions[0][1], *condition_evidence)]}


def _correlated_turn_selection(tree: ast.Module, test) -> dict:
    """Finite, source-derived alternatives for directly guarded version axes.

    Only explicit integer domains and direct raising Boolean comparisons are
    interpreted. This is not an interpreter for delegated validators or state.
    Each row preserves a complete correlated assignment rather than a product
    of independent renderer/version sets.
    """
    from itertools import product
    fail = lambda detail: _not_derived("which conditions make a follow-up turn", detail)
    if not (isinstance(test, ast.Attribute) and ast.unparse(test).startswith('spec.')):
        raise fail('correlated selection requires a direct positive spec axis')
    field = test.attr
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RunSpec'), None)
    init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__post_init__'), None) if cls else None
    if init is None:
        raise fail('missing RunSpec initializer')
    declarations = {n.target.id: n for n in cls.body if isinstance(n, ast.AnnAssign)
                    and isinstance(n.target, ast.Name) and isinstance(n.annotation, ast.Name)
                    and n.annotation.id == 'int'}
    attrs = lambda node: {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
                         and isinstance(n.value, ast.Name) and n.value.id == 'self'}
    dump = lambda n: ast.dump(n, include_attributes=False)
    early = _early_axis_refusal(tree)
    api_fixed = {early['field']: early['api_value']} if early else {}
    # Reduce only comparisons whose operand is proved by the actual early
    # execute refusal. This does not grant a native case or interpret its
    # delegated validation as an API selector.
    def api_test(node):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.left, ast.Attribute) and ast.unparse(node.left.value) == 'self'
                and node.left.attr in api_fixed and isinstance(node.comparators[0], ast.Constant)
                and type(node.comparators[0].value) is int and isinstance(node.ops[0], (ast.Eq, ast.NotEq))):
            equal = api_fixed[node.left.attr] == node.comparators[0].value
            return ast.Constant(equal if isinstance(node.ops[0], ast.Eq) else not equal)
        if isinstance(node, ast.BoolOp):
            values = [api_test(x) for x in node.values]
            if isinstance(node.op, ast.And):
                values = [x for x in values if not (isinstance(x, ast.Constant) and x.value is True)]
            elif isinstance(node.op, ast.Or):
                values = [x for x in values if not (isinstance(x, ast.Constant) and x.value is False)]
            return values[0] if len(values) == 1 else ast.BoolOp(op=node.op, values=values)
        return node
    domains, domain_nodes = {}, {}
    for name, declaration in declarations.items():
        if not (isinstance(declaration.value, ast.Constant) and type(declaration.value.value) is int
                and declaration.value.value == 0):
            continue
        for guard in init.body:
            if not (isinstance(guard, ast.If) and not guard.orelse and len(guard.body) == 1
                    and isinstance(guard.body[0], ast.Raise)):
                continue
            for compare in ast.walk(guard.test):
                if not (isinstance(compare, ast.Compare) and len(compare.ops) == 1
                        and isinstance(compare.ops[0], ast.NotIn) and ast.unparse(compare.left) == f'self.{name}'):
                    continue
                try:
                    values = ast.literal_eval(compare.comparators[0])
                except (ValueError, TypeError):
                    continue
                if (not isinstance(values, (tuple, list)) or not values or 0 not in values
                        or any(type(v) is not int or v < 0 for v in values) or not any(values)):
                    continue
                expected = ast.parse(f'type(self.{name}) is not int or self.{name} not in {values!r}', mode='eval').body
                if dump(guard.test) == dump(expected):
                    if name in domains:
                        raise fail('ambiguous version domain')
                    domains[name], domain_nodes[name] = sorted(set(values)), guard
    if field not in domains:
        raise fail('missing exact integer/default/domain validation')
    if any(sum(isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == name
               for n in cls.body) != 1 for name in domains):
        raise fail('duplicate version field declaration')
    # Only the new nested renderer guard or explicit per-version restrictions
    # activates this grammar. The legacy unsupported-shape tests stay strict.
    candidates = []
    for block in init.body:
        if isinstance(block, ast.If):
            if len(block.body) == 1 and isinstance(block.body[0], ast.Raise) and not block.orelse:
                candidates.append((block, None))
            elif isinstance(block.test, ast.Attribute) and attrs(block.test) <= set(domains):
                for child in block.body:
                    if isinstance(child, ast.If) and (any(isinstance(n, (ast.Raise, ast.Assert, ast.Return))
                            for n in ast.walk(child)) or attrs(child) & (set(domains) | {"condition"})):
                        candidates.append((child, block))
    connected = {field}
    while True:
        expanded = connected | set().union(*(attrs(g.test) | (attrs(p.test) if p else set())
            for g, p in candidates if (attrs(g.test) | (attrs(p.test) if p else set())) & connected)) & set(domains)
        if expanded == connected:
            break
        connected = expanded
    relevant = [(g, p) for g, p in candidates if
                (attrs(g.test) | (attrs(p.test) if p else set())) & connected and g not in domain_nodes.values()]
    nested_renderer = any(p is not None and 'render_version' in attrs(g.test) for g, p in relevant)
    if not nested_renderer:
        raise fail('unsupported optional selector shape')
    if any(isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom, ast.Assert)) for n in ast.walk(init)):
        raise fail('version initializer has an early exit or assertion')
    if any(isinstance(n, ast.Raise) for n in init.body):
        raise fail('version initializer unconditionally raises')
    protected = connected | {'condition'}
    first_domain = min(domain_nodes[name].lineno for name in connected)
    if any(isinstance(n, ast.Attribute) and attrs(n) & {'render_version', 'runtime', 'is_agentic'}
           and isinstance(n.ctx, (ast.Store, ast.Del)) and n.lineno > first_domain for n in ast.walk(init)):
        raise fail('runtime or renderer changes after version admission')
    if any((isinstance(n, ast.Attribute) and attrs(n) & protected and isinstance(n.ctx, (ast.Store, ast.Del)))
           or (isinstance(n, ast.Name) and n.id == 'self' and isinstance(n.ctx, (ast.Store, ast.Del)))
           or _rebinding(n, 'self', init) for n in ast.walk(init)):
        raise fail('correlated selector or spec is reassigned')
    recognized = {id(g) for g, _ in relevant} | {id(p) for _, p in relevant if p} | {id(domain_nodes[n]) for n in connected}
    for node in ast.walk(init):
        if isinstance(node, (ast.If, ast.IfExp, ast.While, ast.Match)):
            condition = node.subject if isinstance(node, ast.Match) else node.test
            if attrs(condition) & connected and id(node) not in recognized:
                # A direct positive block may only call a validator/capture;
                # it cannot contain another unproved selector or condition.
                if not (isinstance(node, ast.If) and node in init.body and isinstance(node.test, ast.Attribute)
                        and node.test.attr in connected and not node.orelse
                        and not any(isinstance(x, (ast.Raise, ast.Assert, ast.Return))
                                    or attrs(x) & {'condition'} for stmt in node.body for x in ast.walk(stmt))):
                    raise fail('unknown correlated guard or selector path')
    for g, parent in relevant:
        if g.orelse or len(g.body) != 1 or not isinstance(g.body[0], ast.Raise):
            raise fail('correlated constraints must be unconditional raising guards')
        if parent is not None:
            if any(isinstance(x, (ast.Raise, ast.Assert, ast.Return, ast.For, ast.Try, ast.With,
                                 ast.FunctionDef, ast.ClassDef)) for x in parent.body):
                raise fail('unproved control flow in positive selector')
            if any('condition' in attrs(x) for x in parent.orelse):
                raise fail('disabled selector carries a condition restriction')
    # A nested exclusive protocol has a reciprocal direct guard for each
    # condition/renderer/companion it requires. Without it, an opaque later
    # validator could invalidate the apparent complementary legacy case.
    for guard, parent in relevant:
        if parent is None:
            continue
        parent_field = parent.test.attr
        enabled = [v for v in domains[parent_field] if v]
        comparisons = [n for n in ast.walk(guard.test) if isinstance(n, ast.Compare)
            and len(n.ops) == 1 and isinstance(n.ops[0], ast.NotEq)
            and isinstance(n.left, ast.Attribute) and isinstance(n.left.value, ast.Name)
            and n.left.value.id == 'self' and isinstance(n.comparators[0], ast.Constant)]
        for compare in comparisons:
            if len(enabled) != 1:
                raise fail('exclusive nested protocol must have one enabled value')
            name, value = compare.left.attr, compare.comparators[0].value
            expected = ast.parse(f'self.{name} == {value!r} and self.{parent_field} != {enabled[0]}',mode='eval').body
            if not any(p is None and dump(api_test(g.test)) == dump(expected) for g,p in relevant):
                raise fail('exclusive nested protocol lacks a reciprocal direct guard')
    constants = {}
    parents = _parents(tree)
    def constant_set(name):
        if name in constants:
            return constants[name]
        bindings = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if len(bindings) != 1:
            raise fail('condition set lacks a unique literal binding')
        binding = bindings[0]; value = binding.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in {'set','frozenset','tuple'}:
            if len(value.args) != 1 or value.keywords or any(_rebinding(n, value.func.id, init)
                    or isinstance(n, ast.Name) and n.id == value.func.id and isinstance(n.ctx, (ast.Store, ast.Del))
                    for n in ast.walk(tree)):
                raise fail('condition set constructor is ambiguous')
            value = value.args[0]
        if not isinstance(value, (ast.Set, ast.List, ast.Tuple)) or not value.elts or any(
                not isinstance(x, ast.Constant) or type(x.value) is not str or not x.value for x in value.elts):
            raise fail('condition set is not a nonempty literal string set')
        for n in ast.walk(tree):
            if _rebinding(n, name, init) or isinstance(n, ast.arg) and n.arg == name:
                raise fail('condition set is shadowed')
            if isinstance(n, ast.Name) and n.id == name and n is not binding.targets[0]:
                parent = parents.get(id(n))
                if not (isinstance(n.ctx, ast.Load) and isinstance(parent, ast.Compare)
                        and len(parent.ops) == 1 and isinstance(parent.ops[0], (ast.In, ast.NotIn))
                        and n is parent.comparators[0]):
                    raise fail('condition set has an unproved use or mutation')
        constants[name] = [x.value for x in value.elts]
        return constants[name]
    def evaluate(node, assignment):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'self':
            if node.attr not in assignment:
                raise fail('unknown field in correlated constraint')
            return assignment[node.attr]
        if isinstance(node, ast.Constant) and type(node.value) in (str, int):
            return node.value
        if isinstance(node, ast.Name):
            return constant_set(node.id)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            # Evaluate every term even when truth values would short-circuit:
            # unknown source syntax may never disappear in a disabled case.
            values = [bool(evaluate(x, assignment)) for x in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = evaluate(node.left, assignment), evaluate(node.comparators[0], assignment)
            op = node.ops[0]
            if isinstance(op, ast.Eq): return type(left) is type(right) and left == right
            if isinstance(op, ast.NotEq): return type(left) is not type(right) or left != right
            if isinstance(op, ast.In) and isinstance(right, list): return left in right
            if isinstance(op, ast.NotIn) and isinstance(right, list): return left not in right
        raise fail('unsupported correlated constraint expression')
    declared_conditions = next((n.value for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'CONDITION_PROMPTS' for t in n.targets)), None)
    if not isinstance(declared_conditions, ast.Dict) or any(not isinstance(k, ast.Constant)
            or type(k.value) is not str for k in declared_conditions.keys):
        raise fail('condition universe must be a literal prompt mapping')
    conditions = sorted(k.value for k in declared_conditions.keys)
    admitted = derive_admitted_renderers(tree)
    refused = derive_execute_refusal(tree, admitted)['refused']
    names = sorted(connected)
    count = len(conditions) * len(admitted) * 2
    for name in names:
        count *= len(domains[name])
    if count > 100000:
        raise fail('correlated selection exceeds finite derivation bound')
    cases = []
    for values in product(*(domains[n] for n in names)):
        axes = dict(zip(names, values))
        if not axes[field]: continue
        allowed = []
        for renderer, native, condition in product(admitted, (False, True), conditions):
            row = {**axes, **api_fixed, 'render_version': renderer, 'is_agentic': native, 'condition': condition}
            violated = []
            for guard, parent in relevant:
                test_value = evaluate(guard.test, row)
                enabled = parent is None or bool(evaluate(parent.test, row))
                violated.append(enabled and bool(test_value))
            if not any(violated): allowed.append((renderer, native, condition))
        if not allowed: continue
        renderers = {r for r, _, _ in allowed}
        if len(renderers) != 1 or any(native for _, native, _ in allowed) or renderers & set(refused):
            raise fail('each correlated case requires one admitted API-only renderer')
        cases.append({'values': axes, 'runtime': 'api', 'renderers': sorted(renderers),
                      'conditions': sorted({c for _, _, c in allowed})})
    if {c['values'][field] for c in cases} != set(domains[field]) - {0}:
        raise fail('enabled version domain has an unproved or impossible case')
    evidence = sorted({declarations[n].lineno for n in names} | {domain_nodes[n].lineno for n in names}
                      | {g.lineno for g, _ in relevant} | {p.lineno for _, p in relevant if p})
    return {'field': field, 'default': 0, 'enabled_values': [v for v in domains[field] if v],
            'runtime': 'api', 'renderers': sorted({r for c in cases for r in c['renderers']}),
            'conditions': sorted({v for c in cases for v in c['conditions']}), 'cases': cases,
            'evidence': [f'api_runner.py:{line}' for line in evidence]}


def _delegated_turn_selection(tree: ast.Module, test, root: Path) -> dict:
    """Prove the fixed shared selector's closed tuples from source (#4503).

    This deliberately does not execute a validator, interpret arbitrary Python,
    or use a known renderer/condition table as a fallback.
    """
    from itertools import product
    fail = lambda detail: _not_derived('which conditions make a follow-up turn', detail)
    dump = lambda node: ast.dump(node, include_attributes=False)
    same = lambda node, text: dump(node) == dump(ast.parse(text).body[0])
    attrs = lambda node, owner='self': {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
        and isinstance(n.value, ast.Name) and n.value.id == owner}
    if root is None or not (isinstance(test, ast.Attribute) and ast.unparse(test).startswith('spec.')):
        raise fail('delegated selection needs an actual source root and direct positive axis')
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RunSpec'), None)
    init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__post_init__'), None) if cls else None
    if init is None:
        raise fail('missing delegated selector constructor')
    helper_path = root / 'src/data_sheets_schema/shared_generation.py'
    helper_tree = _tree(helper_path)
    helper = _function(helper_tree, 'select')
    if helper is None or _params(helper) != ['spec']:
        raise fail('shared selector signature changed')
    # Resolve the effective exported definition, not merely the first AST.
    # Reuse the scanner's binding classifier for imports/defs/args/global names.
    def effective_definition(source, definition, name):
        if (definition is None or definition not in source.body or definition.decorator_list
                or sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                       and n.name == name for n in source.body) != 1):
            raise fail('selector authority is not one undecorated effective definition')
        for node in ast.walk(source):
            if (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del))) \
                    or _rebinding(node, name, definition):
                raise fail('selector authority is shadowed or rebound')
            if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
                raise fail('selector authority has an unproved wildcard import')
    effective_definition(helper_tree, helper, 'select')
    for source, owner, builtins in ((helper_tree, helper, ('getattr', 'type', 'int', 'str')),
                                    (tree, init, ('type', 'int'))):
        for name in builtins:
            if any(_rebinding(node, name, owner) or isinstance(node, ast.arg) and node.arg == name
                    or isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del))
                    for node in ast.walk(source)):
                raise fail('selector builtin identity is shadowed')
    body = helper.body
    if len(body) != 9:
        raise fail('unsupported shared selector body')
    if not (isinstance(body[0], ast.Assign) and len(body[0].targets) == 1
            and isinstance(body[0].targets[0], ast.Name) and body[0].targets[0].id == 'version'
            and isinstance(body[0].value, ast.Call) and ast.unparse(body[0].value.func) == 'getattr'
            and len(body[0].value.args) == 3 and not body[0].value.keywords
            and ast.unparse(body[0].value.args[0]) == 'spec'
            and isinstance(body[0].value.args[1], ast.Constant)
            and type(body[0].value.args[1].value) is str
            and ast.literal_eval(body[0].value.args[2]) == 0):
        raise fail('shared selector lacks its exact version binding')
    axis = body[0].value.args[1].value

    def raising(node):
        return (isinstance(node, ast.If) and not node.orelse and len(node.body) == 1
                and isinstance(node.body[0], ast.Raise))

    domain_guard = body[1]
    if not raising(domain_guard):
        raise fail('shared selector domain must raise directly')
    try:
        domain = ast.literal_eval(domain_guard.test.values[1].comparators[0])
    except (AttributeError, IndexError, ValueError, TypeError):
        raise fail('shared selector lacks a finite integer domain')
    if (type(domain) is not tuple or len(domain) != 3 or len(set(domain)) != 3 or 0 not in domain
            or any(type(v) is not int or v < 0 for v in domain)
            or dump(domain_guard.test) != dump(ast.parse(
                f'type(version) is not int or version not in {domain!r}', mode='eval').body)):
        raise fail('shared selector domain is not exact')
    if not same(body[2], 'registration = getattr(spec, "shared_generation_registration", None)'):
        raise fail('shared registration binding changed')
    if not same(body[3], 'from .source_heading_runtime import MODES'):
        raise fail('shared condition map import changed')
    modes_path = root / 'src/data_sheets_schema/source_heading_runtime.py'
    modes_tree = _tree(modes_path)
    declarations = [n for n in modes_tree.body if isinstance(n, ast.Assign)
        and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'MODES']
    if len(declarations) != 1:
        raise fail('condition map has no unique declaration')
    modes_line = declarations[0].lineno
    try:
        modes = ast.literal_eval(declarations[0].value)
    except (ValueError, TypeError):
        raise fail('condition map is not literal')
    if (type(modes) is not dict or not modes or any(type(k) is not str or not k
            or type(v) is not str or not v for k, v in modes.items())
            or len(set(modes.values())) != len(modes)):
        raise fail('condition map must have unique nonempty literal names')
    if (not isinstance(declarations[0].value, ast.Dict)
            or len(declarations[0].value.keys) != len(modes)):
        raise fail('condition map repeats a literal key')
    modes_parents = _parents(modes_tree)
    for node in ast.walk(modes_tree):
        if _rebinding(node, 'MODES', helper) or isinstance(node, ast.arg) and node.arg == 'MODES':
            raise fail('condition map is shadowed')
        if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
            raise fail('condition map has an unproved wildcard import')
        if isinstance(node, ast.Name) and node.id == 'MODES' and node is not declarations[0].targets[0]:
            parent = modes_parents.get(id(node))
            membership = (isinstance(parent, ast.Compare) and len(parent.ops) == 1
                and isinstance(parent.ops[0], (ast.In, ast.NotIn)) and node is parent.comparators[0])
            lookup = (isinstance(parent, ast.Subscript) and parent.value is node
                and isinstance(parent.ctx, ast.Load))
            if not (isinstance(node.ctx, ast.Load) and (membership or lookup)):
                raise fail('condition map has an unproved use, escape or mutation')
    for node in ast.walk(helper):
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
            raise fail('shared selector mutates an input')
        if isinstance(node, ast.Name) and node.id in {'MODES', 'spec', 'getattr', 'type', 'int', 'str', 'descriptor'} \
                and isinstance(node.ctx, (ast.Store, ast.Del)):
            raise fail('shared selector shadows an authority')

    def tuple_guard(guard):
        if not raising(guard) or not isinstance(guard.test, ast.BoolOp) or not isinstance(guard.test.op, ast.Or):
            raise fail('shared tuple is not an unconditional OR refusal')
        required = {}
        for term in guard.test.values:
            if isinstance(term, ast.Attribute) and ast.unparse(term).startswith('spec.'):
                key, value = term.attr, 0
            elif (isinstance(term, ast.Compare) and len(term.ops) == 1
                    and isinstance(term.left, ast.Attribute) and ast.unparse(term.left).startswith('spec.')):
                key = term.left.attr
                if isinstance(term.ops[0], ast.NotEq) and isinstance(term.comparators[0], ast.Constant):
                    value = term.comparators[0].value
                    if type(value) not in (str, int):
                        raise fail('unsupported tuple literal')
                elif (key == 'condition' and isinstance(term.ops[0], ast.NotIn)
                        and ast.unparse(term.comparators[0]) == 'MODES.values()'):
                    value = tuple(sorted(modes.values()))
                else:
                    raise fail('unsupported shared tuple comparison')
            else:
                raise fail('unsupported shared tuple term')
            if key in required:
                raise fail('duplicate shared tuple field')
            required[key] = value
        if not {'condition', 'render_version', 'runtime'} <= required.keys():
            raise fail('shared tuple omits condition, renderer or runtime')
        return required

    branch = body[5]
    if not (isinstance(branch, ast.If) and not branch.orelse and len(branch.body) == 3
            and isinstance(branch.test, ast.Compare) and len(branch.test.ops) == 1
            and isinstance(branch.test.ops[0], ast.Eq) and ast.unparse(branch.test.left) == 'version'
            and isinstance(branch.test.comparators[0], ast.Constant)):
        raise fail('unsupported enabled shared branch')
    explicit = branch.test.comparators[0].value
    if type(explicit) is not int or explicit not in set(domain) - {0}:
        raise fail('enabled shared branch is outside its domain')
    implicit = next(v for v in domain if v not in (0, explicit))
    protocols = {explicit: tuple_guard(branch.body[0]), implicit: tuple_guard(body[6])}
    registration_test = ast.parse('type(registration) is not str or not registration', mode='eval').body
    for guard in (branch.body[1], body[7]):
        if not raising(guard) or dump(guard.test) != dump(registration_test):
            raise fail('shared branch loses its required registration')
    if not same(branch.body[2], f'return descriptor(version={explicit!r}, condition=spec.condition)') \
            or not same(body[8], 'return descriptor()'):
        raise fail('shared descriptor return is not bound to its branch')
    descriptor_fn = _function(helper_tree, 'descriptor')
    effective_definition(helper_tree, descriptor_fn, 'descriptor')
    defaults = dict(zip((a.arg for a in descriptor_fn.args.kwonlyargs), descriptor_fn.args.kw_defaults)) if descriptor_fn else {}
    if not isinstance(defaults.get('version'), ast.Constant) or defaults['version'].value != implicit:
        raise fail('implicit shared branch differs from descriptor default')
    zero = body[4]
    if not (isinstance(zero, ast.If) and not zero.orelse and ast.unparse(zero.test) == 'not version'
            and same(zero.body[-1], 'return None')):
        raise fail('disabled shared branch changed')
    zero_body = zero.body[:-1]
    native_evidence = []
    native_domain = None
    if len(zero_body) == 2:
        native = zero_body.pop(0)
        expected = ast.parse("if getattr(spec, 'native_shared_generation_version', 0):\n    from .native_shared_render import validate_spec\n    validate_spec(spec)\n    return None").body[0]
        if dump(native) != dump(expected):
            raise fail('unsupported separate native dispatch')
        native_path = root / 'src/data_sheets_schema/native_shared_render.py'
        native_tree = _tree(native_path)
        native_fn = _function(native_tree, 'validate_spec')
        effective_definition(native_tree, native_fn, 'validate_spec')
        for builtin in ('getattr', 'type', 'int', 'str'):
            if any(_rebinding(n, builtin, native_fn) or isinstance(n, ast.arg) and n.arg == builtin
                    or isinstance(n, ast.Name) and n.id == builtin and isinstance(n.ctx, (ast.Store, ast.Del))
                    for n in ast.walk(native_tree)):
                raise fail('native selector builtin identity is shadowed')
        native_axis = 'native_shared_generation_version'
        prefix = native_fn.body[:6]
        if (_params(native_fn) != ['spec'] or len(prefix) != 6
                or not same(prefix[0], f'version = getattr(spec, {native_axis!r}, 0)')
                or not same(prefix[1], 'registration = getattr(spec, "native_shared_generation_registration", None)')
                or not raising(prefix[2]) or not isinstance(prefix[3], ast.If)
                or ast.unparse(prefix[3].test) != 'not version' or prefix[3].orelse
                or len(prefix[3].body) != 2 or not raising(prefix[3].body[0])
                or not same(prefix[3].body[1], 'return None') or not raising(prefix[4])):
            raise fail('native selector does not reach its zero-axis loop through proved refusals')
        try:
            native_domain = ast.literal_eval(prefix[2].test.values[1].comparators[0])
        except (AttributeError, IndexError, ValueError, TypeError):
            raise fail('native selector lacks a finite integer domain')
        if (type(native_domain) is not tuple or len(native_domain) != 2 or 0 not in native_domain
                or any(type(v) is not int or v < 0 for v in native_domain) or len(set(native_domain)) != 2
                or dump(prefix[2].test) != dump(ast.parse(
                    f'type(version) is not int or version not in {native_domain!r}', mode='eval').body)):
            raise fail('native selector domain is not exact')
        for expression in (prefix[0].value, prefix[1].value, prefix[2].test,
                           prefix[3].test, prefix[3].body[0].test, prefix[4].test):
            for node in ast.walk(expression):
                if (isinstance(node, ast.Call) and ast.unparse(node.func) not in {'getattr', 'type'}
                        or isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del))):
                    raise fail('unproved work before native zero-axis validation')
        loop = prefix[5]
        if (not isinstance(loop, ast.For) or loop.orelse or ast.unparse(loop.target) != 'key'
                or len(loop.body) != 1 or not raising(loop.body[0])
                or ast.unparse(loop.body[0].test) != 'type(getattr(spec, key)) is not int or getattr(spec, key) != 0'):
            raise fail('native zero-axis loop is not unconditional and exact')
        try:
            zero_axes = ast.literal_eval(loop.iter)
        except (ValueError, TypeError):
            raise fail('native zero-axis roster is not literal')
        if (type(zero_axes) is not tuple or any(type(v) is not str for v in zero_axes)
                or len(set(zero_axes)) != len(zero_axes) or test.attr not in zero_axes
                or axis not in zero_axes or 'receipt_completion_version' not in zero_axes):
            raise fail('native dispatch does not exclude API companion axes')
        if any(isinstance(n, ast.Attribute) and attrs(n, 'spec') and isinstance(n.ctx, (ast.Store, ast.Del))
               or isinstance(n, ast.Name) and n.id == 'spec' and isinstance(n.ctx, (ast.Store, ast.Del))
               or _rebinding(n, 'spec', native_fn) for n in ast.walk(native_fn)):
            raise fail('native selector mutates its validated spec')
        native_evidence = [f'{_rel(root, native_path)}:{native_fn.lineno}',
                           f'{_rel(root, native_path)}:{loop.lineno}']
    if len(zero_body) != 1 or not raising(zero_body[0]) or not isinstance(zero_body[0].test, ast.BoolOp) \
            or not isinstance(zero_body[0].test.op, ast.Or):
        raise fail('disabled shared exclusions changed')
    exclusions = set()
    for term in zero_body[0].test.values:
        if ast.unparse(term) == 'registration is not None':
            exclusions.add(('registration', None))
        elif (isinstance(term, ast.Compare) and len(term.ops) == 1
                and isinstance(term.left, ast.Attribute) and ast.unparse(term.left).startswith('spec.')):
            if isinstance(term.ops[0], ast.Eq) and isinstance(term.comparators[0], ast.Constant):
                exclusions.add((term.left.attr, term.comparators[0].value))
            elif term.left.attr == 'condition' and isinstance(term.ops[0], ast.In) \
                    and ast.unparse(term.comparators[0]) == 'MODES.values()':
                exclusions.update(('condition', value) for value in modes.values())
            else: raise fail('unsupported disabled shared comparison')
        else: raise fail('unsupported disabled shared exclusion')
    expected_exclusions = {('registration', None)}
    for required in protocols.values():
        for name, value in required.items():
            if name == 'runtime' or value == 0: continue
            expected_exclusions.update((name, item) for item in (value if type(value) is tuple else (value,)))
    if exclusions != expected_exclusions:
        raise fail('disabled shared exclusions do not cover exactly its enabled tuples')

    imports = [n for n in ast.walk(init) if isinstance(n, ast.ImportFrom) and n.module == 'shared_generation'
               and n.level == 1 and any(a.name == 'select' for a in n.names)]
    if len(imports) != 2:
        raise fail('constructor lacks its two exact shared selector calls')
    parent_map = _parents(init)
    calls = []
    for imported in imports:
        if len(imported.names) != 1:
            raise fail('ambiguous shared selector import')
        alias = imported.names[0].asname or 'select'
        uses = [n for n in ast.walk(init) if isinstance(n, ast.Call) and ast.unparse(n.func) == alias]
        if len(uses) != 1 or ast.unparse(uses[0]) != alias + '(self)':
            raise fail('shared selector is not called once with the same spec')
        _require_followup_binding(RUNNER, tree, init, uses[0])
        calls.append(uses[0])
    guarded = [call for call in calls if any(isinstance(n, ast.If) and ast.unparse(n.test) == 'self.' + axis
        and len(n.body) == 2 and n.body[0] in imports and isinstance(n.body[1], ast.Expr)
        and n.body[1].value is call and not n.orelse for n in init.body)]
    final = [call for call in calls if isinstance(parent_map.get(id(call)), ast.Expr)
        and parent_map.get(id(parent_map[id(call)])) is init]
    if len(guarded) != 1 or len(final) != 1 or final[0].lineno <= guarded[0].lineno:
        raise fail('shared selector call guards/order changed')

    inactive_native = {}
    if native_domain is not None:
        native_imports = [n for n in init.body if isinstance(n, ast.ImportFrom)
            and n.level == 1 and n.module == 'native_shared_render'
            and len(n.names) == 1 and n.names[0].name == 'validate_spec']
        if len(native_imports) != 1:
            raise fail('native domain lacks its unconditional constructor import')
        imported = native_imports[0]
        alias = imported.names[0].asname or imported.names[0].name
        index = init.body.index(imported)
        following = init.body[index + 1] if index + 1 < len(init.body) else None
        if (not isinstance(following, ast.Expr) or not isinstance(following.value, ast.Call)
                or ast.unparse(following.value) != alias + '(self)'
                or following.lineno >= min(call.lineno for call in calls)):
            raise fail('native domain is not validated on the same spec before shared admission')
        _require_followup_binding(RUNNER, tree, init, following.value)
        native_declarations = [n for n in cls.body if isinstance(n, ast.AnnAssign)
            and isinstance(n.target, ast.Name) and n.target.id == native_axis]
        if (len(native_declarations) != 1 or ast.unparse(native_declarations[0].annotation) != 'int'
                or not isinstance(native_declarations[0].value, ast.Constant)
                or type(native_declarations[0].value.value) is not int or native_declarations[0].value.value != 0):
            raise fail('native selector lacks its exact inactive default')
        if any(isinstance(n, ast.Attribute) and native_axis in attrs(n) and isinstance(n.ctx, (ast.Store, ast.Del))
                and n.lineno > following.lineno for n in ast.walk(init)):
            raise fail('native selector changes after its domain validation')
        # The reached validator rejects every positive native choice when
        # this requested API axis is positive. Its only surviving value is0.
        inactive_native[native_axis] = 0
        native_evidence.append(f'api_runner.py:{following.lineno}')

    declarations = {n.target.id: n for n in cls.body if isinstance(n, ast.AnnAssign)
        and isinstance(n.target, ast.Name) and isinstance(n.annotation, ast.Name) and n.annotation.id == 'int'}
    domains, domain_nodes = {}, {}
    for node in init.body:
        if not raising(node) or not isinstance(node.test, ast.BoolOp): continue
        try:
            compare = node.test.values[1]
            field = compare.left.attr
            values = ast.literal_eval(compare.comparators[0])
        except (AttributeError, IndexError, ValueError, TypeError): continue
        if dump(node.test) != dump(ast.parse(f'type(self.{field}) is not int or self.{field} not in {values!r}', mode='eval').body): continue
        declaration = declarations.get(field)
        if (declaration is None or not isinstance(declaration.value, ast.Constant) or type(declaration.value.value) is not int
                or declaration.value.value != 0 or type(values) is not tuple or not values or 0 not in values
                or any(type(v) is not int or v < 0 for v in values) or field in domains):
            raise fail('delegated axes lack exact unique integer/default/domain guards')
        domains[field], domain_nodes[field] = sorted(set(values)), node
    if domains.get(axis) != sorted(domain) or test.attr not in domains:
        raise fail('constructor/helper domain differs or requested axis is unproved')
    names = sorted(domains)
    semantic = set(names) | set(inactive_native) | {'condition', 'render_version', 'runtime', 'is_agentic'}
    first_domain = min(n.lineno for n in domain_nodes.values())
    if any(isinstance(n, ast.Attribute) and attrs(n) & semantic and isinstance(n.ctx, (ast.Store, ast.Del))
           and n.lineno > first_domain for n in ast.walk(init)):
        raise fail('constructor mutates a selected axis after admission')
    if any(isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom, ast.Assert)) for n in ast.walk(init)):
        raise fail('constructor bypasses delegated admission')

    constants = {}
    literal_parents = _parents(tree)
    def constant_set(name):
        if name in constants: return constants[name]
        bindings = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if len(bindings) != 1: raise fail('selector set lacks one literal binding')
        binding = bindings[0]
        value = binding.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in {'set','frozenset','tuple'}:
            if len(value.args) != 1 or value.keywords or any(_rebinding(n, value.func.id, init)
                    or isinstance(n, ast.Name) and n.id == value.func.id and isinstance(n.ctx, (ast.Store, ast.Del))
                    for n in ast.walk(tree)):
                raise fail('selector set constructor is ambiguous')
            value = value.args[0]
        if not isinstance(value, (ast.Set, ast.Tuple, ast.List)) or not value.elts or any(
                not isinstance(n, ast.Constant) or type(n.value) is not str or not n.value for n in value.elts):
            raise fail('selector set is not a nonempty literal string set')
        # Same finite membership-only uses as the legacy correlated reader.
        for node in ast.walk(tree):
            if _rebinding(node, name, init) or isinstance(node, ast.arg) and node.arg == name:
                raise fail('selector set is shadowed')
            if isinstance(node, ast.Name) and node.id == name and node is not binding.targets[0]:
                parent = literal_parents.get(id(node))
                if not (isinstance(node.ctx, ast.Load) and isinstance(parent, ast.Compare)
                        and len(parent.ops) == 1 and isinstance(parent.ops[0], (ast.In, ast.NotIn))
                        and node is parent.comparators[0]):
                    raise fail('selector set has an unproved use, escape or mutation')
        constants[name] = tuple(n.value for n in value.elts)
        return constants[name]

    def evaluate(node, row):
        if isinstance(node, ast.Attribute) and ast.unparse(node).startswith('self.') and node.attr in row:
            return row[node.attr]
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, bool): return node.value
        if isinstance(node, ast.Name): return constant_set(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return not evaluate(node.operand, row)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            values = [bool(evaluate(n, row)) for n in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            a, b = evaluate(node.left, row), evaluate(node.comparators[0], row)
            if isinstance(node.ops[0], ast.Eq): return type(a) is type(b) and a == b
            if isinstance(node.ops[0], ast.NotEq): return type(a) is not type(b) or a != b
            if isinstance(node.ops[0], ast.In): return a in b
            if isinstance(node.ops[0], ast.NotIn): return a not in b
        raise fail('unsupported delegated constructor constraint')
    constraints = []
    parents = _parents(init)
    for node in ast.walk(init):
        if not raising(node) or node in domain_nodes.values() or not (attrs(node.test) & (set(names) | {'condition'})):
            continue
        chain, child = [(node.test, True)], node
        while id(child) in parents:
            parent = parents[id(child)]
            if isinstance(parent, ast.If):
                chain.append((parent.test, child in parent.body))
            child = parent
        constraints.append((node, chain))
    # _module_constants intentionally does not evaluate prompt Paths; only keys
    # of the actual literal mapping determine the complete condition universe.
    mapping = next((n.value for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'CONDITION_PROMPTS' for t in n.targets)), None)
    if not isinstance(mapping, ast.Dict) or any(not isinstance(k, ast.Constant) or type(k.value) is not str for k in mapping.keys):
        raise fail('condition universe is not literal')
    conditions = sorted(k.value for k in mapping.keys)
    admitted = derive_admitted_renderers(tree)
    refused = set(derive_execute_refusal(tree, admitted)['refused'])
    agentic = constant_set('AGENTIC_RUNTIMES')
    is_agentic = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'is_agentic'), None)
    agentic_returns = [n for n in is_agentic.body if not isinstance(n, ast.Expr)] if is_agentic else []
    if len(agentic_returns) != 1 or not same(agentic_returns[0], 'return self.runtime in AGENTIC_RUNTIMES'):
        raise fail('agentic property does not use the proved runtime set')
    for required in protocols.values():
        if type(required['runtime']) is not str or required['runtime'] in agentic:
            raise fail('shared tuple is not API-only')
        wanted = required['condition'] if type(required['condition']) is tuple else (required['condition'],)
        if not set(wanted) <= set(conditions): raise fail('shared conditions are outside the actual prompt universe')

    def clauses(node):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            result = [clause for term in node.values for clause in clauses(term)]
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            result = [[]]
            for term in node.values: result = [a+b for a in result for b in clauses(term)]
        else: result = [[node]]
        if len(result) > 64: raise fail('reciprocal guard exceeds finite clause bound')
        return result

    reciprocal = []
    for _, chain in constraints:
        if not all(polarity for _, polarity in chain): continue
        combined = [[]]
        for expr, _ in chain: combined = [a+b for a in combined for b in clauses(expr)]
        reciprocal += combined
    for version, required in protocols.items():
        wrong = dump(ast.parse(f'self.{axis} != {version!r}', mode='eval').body)
        for name, value in required.items():
            if name == 'runtime' or value == 0: continue
            for wanted in (value if type(value) is tuple else (value,)):
                matched = False
                for clause in reciprocal:
                    if inactive_native:
                        enabled_native = next(value for value in native_domain if value)
                        inactive_fact = dump(ast.parse(f'self.{native_axis} != {enabled_native}', mode='eval').body)
                        clause = [term for term in clause if dump(term) != inactive_fact]
                    if len(clause) != 2 or not any(dump(term) == wrong for term in clause): continue
                    atom = next(term for term in clause if dump(term) != wrong)
                    if not (isinstance(atom, ast.Compare) and len(atom.ops) == 1
                            and ast.unparse(atom.left) == 'self.' + name): continue
                    if isinstance(atom.ops[0], ast.Eq) and isinstance(atom.comparators[0], ast.Constant):
                        matched |= type(atom.comparators[0].value) is type(wanted) and atom.comparators[0].value == wanted
                    elif name == 'condition' and isinstance(atom.ops[0], ast.In) and isinstance(atom.comparators[0], ast.Name):
                        matched |= wanted in constant_set(atom.comparators[0].id)
                if not matched: raise fail('shared tuple lacks an exact reciprocal constructor guard')
    cases, evaluations = [], 0
    for values in product(*(domains[n] for n in names)):
        axes = {**dict(zip(names, values)), **inactive_native}
        if not axes[test.attr]: continue
        version = axes[axis]
        required = protocols.get(version)
        if required and any(name in axes and axes[name] != value for name, value in required.items()): continue
        renderers = [required['render_version']] if required else admitted
        allowed = []
        for renderer, native, condition in product(renderers, (False, True), conditions):
            evaluations += 1
            if evaluations > 100000: raise fail('delegated selection exceeds finite derivation bound')
            row = {**axes, 'render_version':renderer, 'is_agentic':native, 'condition':condition}
            violations = [all([bool(evaluate(expr, row)) == polarity for expr, polarity in chain])
                          for _, chain in constraints]
            if any(violations): continue
            if required:
                wanted = required['condition'] if type(required['condition']) is tuple else (required['condition'],)
                if native or condition not in wanted: continue
            elif any((name, row.get(name)) in exclusions for name in row): continue
            allowed.append((renderer, native, condition))
        if not allowed: continue
        renderers = {r for r, _, _ in allowed}
        if len(renderers) != 1 or any(n for _, n, _ in allowed) or renderers & refused:
            raise fail('delegated case lacks one admitted API-only renderer')
        extra = {name:value for name,value in (required or {}).items() if name not in semantic}
        if any(type(value) is not int or value != 0 or name not in declarations for name,value in extra.items()):
            raise fail('unproved companion selector')
        cases.append({'values':{**axes, **extra},'runtime':'api','renderers':sorted(renderers),
                      'conditions':sorted({c for _,_,c in allowed})})
    if {case['values'][test.attr] for case in cases} != set(domains[test.attr]) - {0}:
        raise fail('delegated enabled domain has an impossible or unproved case')
    evidence = [f'api_runner.py:{node.lineno}' for node in [*domain_nodes.values(), *calls, *[n for n,_ in constraints]]]
    evidence += [f'{_rel(root, helper_path)}:{helper.lineno}', f'{_rel(root, modes_path)}:{modes_line}', *native_evidence]
    return {'field':test.attr,'default':0,'enabled_values':[v for v in domains[test.attr] if v],
            'runtime':'api','renderers':sorted({r for c in cases for r in c['renderers']}),
            'conditions':sorted({v for c in cases for v in c['conditions']}),'cases':cases,'evidence':sorted(set(evidence))}


def _optional_turn_selection(tree: ast.Module, test, *, root=None) -> dict:
    try:
        return _simple_optional_turn_selection(tree, test)
    except ConfigError as original:
        try:
            return _correlated_turn_selection(tree, test)
        except ConfigError as changed:
            if root is not None:
                cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RunSpec'), None)
                init = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__post_init__'), None) if cls else None
                if init is not None and any(isinstance(n, ast.ImportFrom) and n.module == 'shared_generation'
                        and any(a.name == 'select' for a in n.names) for n in ast.walk(init)):
                    return _delegated_turn_selection(tree, test, root)
            if "unsupported optional selector shape" in str(changed):
                raise original
            raise


def _local_plan_scopes(tree: ast.Module, consts: dict, *, root=None) -> dict:
    """Condition and explicit opt-in selection, from plan()'s actual syntax."""
    plan = _function(tree, "plan")
    if plan is None:
        raise _not_derived("which conditions make a follow-up turn", "api_runner.py defines no plan()")
    value = next((v for n in ast.walk(plan) if isinstance(n, ast.Dict) for k, v in zip(n.keys, n.values)
                  if isinstance(k, ast.Constant) and k.value == "conditional_calls"), None)
    if value is None:
        raise _not_derived("which conditions make a follow-up turn", "plan() lists no conditional_calls")
    scopes = {}

    def gate_of(test):
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            left, op, right = test.left, test.ops[0], test.comparators[0]
            if ast.unparse(left) == "spec.condition":
                if (isinstance(op, ast.In) and isinstance(right, ast.Name)
                        and isinstance(consts.get(right.id), tuple)
                        and all(isinstance(v, str) for v in consts[right.id])):
                    return {"conditions": sorted(consts[right.id])}
                if isinstance(op, ast.Eq) and isinstance(right, ast.Constant) and isinstance(right.value, str):
                    return {"conditions": [right.value]}
        selection = _optional_turn_selection(tree, test, root=root)
        return {"conditions": selection.get("conditions"), "selection": selection}

    def visit(node, gate):
        if isinstance(node, ast.IfExp):
            if gate or not isinstance(node.orelse, (ast.List, ast.Tuple)) or node.orelse.elts:
                raise _not_derived("which conditions make a follow-up turn", "nested or nonempty alternative gate")
            visit(node.body, gate_of(node.test))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            m = re.match(r"(\w+):", node.value)
            if m:
                if m.group(1) in scopes:
                    raise _not_derived("which conditions make a follow-up turn", "duplicate planned turn")
                scopes[m.group(1)] = gate or {"conditions": None}
        elif isinstance(node, ast.JoinedStr):
            if node.values and isinstance(node.values[0], ast.Constant):
                visit(node.values[0], gate)
        elif isinstance(node, (ast.List, ast.Tuple)):
            for child in node.elts:
                visit(child, gate)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            visit(node.left, gate)
            visit(node.right, gate)
        else:
            raise _not_derived("which conditions make a follow-up turn",
                               f"unreadable conditional_calls expression `{ast.unparse(node)[:60]}`")

    visit(value, None)
    return scopes


def _literal_phase(root, path, tree, fn, node):
    """One literal phase binding, optionally imported at this exact use."""
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return node.value
    if not isinstance(node, ast.Name):
        raise _not_derived('the follow-up turns', 'phase is not a literal or uniquely bound constant')
    name = node.id
    bindings = _bindings(root, path, tree, {})
    if name in bindings:
        _require_followup_binding(_rel(root, path), tree, fn, node)
        target, name = bindings[name]
        if name is None:
            raise _not_derived('the follow-up turns', 'phase import names a module')
        tree = _tree(target)
    else:
        if name in _params(fn) or any(isinstance(n, ast.Name) and n.id == name
                and isinstance(n.ctx, (ast.Store, ast.Del)) for n in ast.walk(fn)):
            raise _not_derived('the follow-up turns', 'phase constant is locally shadowed')
    declarations = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
    if (len(declarations) != 1 or not isinstance(declarations[0].value, ast.Constant)
            or type(declarations[0].value.value) is not str):
        raise _not_derived('the follow-up turns', 'phase constant lacks one literal binding')
    declaration = declarations[0]
    if any((_rebinding(n, name, fn) or isinstance(n, ast.Name) and n.id == name
            and isinstance(n.ctx, (ast.Store, ast.Del)) and n is not declaration.targets[0]) for n in ast.walk(tree)):
        raise _not_derived('the follow-up turns', 'phase constant is reassigned')
    return declaration.value.value


def _delegated_plan(root, tree):
    """Read one directly returned optional plan without interpreting its code."""
    plan = _function(tree, 'plan')
    branches = [n for n in plan.body if isinstance(n, ast.If) and any(isinstance(x, ast.Return)
                for x in ast.walk(n))]
    if not branches:
        return None
    if len(branches) != 1:
        raise _not_derived('the optional plan', 'ambiguous early plan routes')
    branch = branches[0]
    if (branch.orelse or len(branch.body) != 2 or not isinstance(branch.body[0], ast.ImportFrom)
            or not isinstance(branch.body[1], ast.Return) or not isinstance(branch.body[1].value, ast.Call)):
        raise _not_derived('the optional plan', 'expected exact import and early delegate return')
    call = branch.body[1].value
    selection = _optional_turn_selection(tree, branch.test, root=root)
    runner = _resolved(root / RUNNER)
    binding = _imported_target(call, _bindings(root, runner, tree, {}))
    if binding is None or binding[1] is None:
        raise _not_derived('the optional plan', 'delegate is not a uniquely imported function')
    _require_followup_binding(RUNNER, tree, plan, call)
    guards = _optional_guard_evidence(plan, call, selection, RUNNER)
    if not guards:
        raise _not_derived('the optional plan', 'delegate lacks a positive selector')
    target, name = binding
    helper_tree = _tree(target); helper = _function(helper_tree, name)
    passed = _call_arg(call, helper, 'spec') if helper is not None else None
    if not isinstance(passed, ast.Name) or passed.id != 'spec':
        raise _not_derived('the optional plan', 'delegate receives another spec')
    if any((isinstance(n, ast.Name) and n.id == 'spec' and isinstance(n.ctx, (ast.Store, ast.Del)))
            or (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'spec'
                and isinstance(n.ctx, (ast.Store, ast.Del))) for n in ast.walk(helper)):
        raise _not_derived('the optional plan', 'delegate reassigns its spec')
    if any(isinstance(n, (ast.Raise, ast.Assert)) for n in helper.body):
        raise _not_derived('the optional plan', 'delegate unconditionally refuses')
    returns = [n for n in ast.walk(helper) if isinstance(n, ast.Return)]
    if len(returns) != 1 or returns[0] not in helper.body or not isinstance(returns[0].value, ast.Dict):
        raise _not_derived('the optional plan', 'delegate must return its one literal plan dictionary')
    keys = [k.value if isinstance(k, ast.Constant) else None for k in returns[0].value.keys]
    if keys.count('conditional_calls') != 1:
        raise _not_derived('the optional plan', 'delegate lacks unique conditional_calls')
    value = returns[0].value.values[keys.index('conditional_calls')]
    if not isinstance(value, (ast.List, ast.Tuple)):
        raise _not_derived('the optional plan', 'delegate phases must be a literal sequence')
    phases = []
    for item in value.elts:
        if isinstance(item, ast.Constant) and type(item.value) is str:
            text = item.value
        elif (isinstance(item, ast.JoinedStr) and len(item.values) >= 2
                and isinstance(item.values[0], ast.FormattedValue)
                and item.values[0].conversion == -1 and item.values[0].format_spec is None
                and isinstance(item.values[1], ast.Constant) and type(item.values[1].value) is str):
            text = _literal_phase(root, target, helper_tree, helper, item.values[0].value) + item.values[1].value
            if not re.match(r'^\w+:', text):
                raise _not_derived('the optional plan', 'phase prefix is not fixed before description interpolation')
            axes = {key for case in selection.get('cases', []) for key in case['values']}
            for suffix in item.values[2:]:
                if isinstance(suffix, ast.Constant) and type(suffix.value) is str:
                    continue
                if not (isinstance(suffix, ast.FormattedValue) and suffix.conversion == -1
                        and suffix.format_spec is None and isinstance(suffix.value, ast.Attribute)
                        and ast.unparse(suffix.value) == 'spec.' + suffix.value.attr
                        and suffix.value.attr in axes):
                    raise _not_derived('the optional plan', 'description interpolation is not a proved finite selector')
        else:
            raise _not_derived('the optional plan', 'unknown delegated phase expression')
        match = re.match(r'^(\w+):', text)
        if match is None or match.group(1) in phases:
            raise _not_derived('the optional plan', 'duplicate or missing exact phase-colon prefix')
        phases.append(match.group(1))
    # The legacy return must remain the single unconditional alternative.
    if len([n for n in ast.walk(plan) if isinstance(n, ast.Return)]) != 2 or not (
            isinstance(plan.body[-1], ast.Return) and isinstance(plan.body[-1].value, ast.Dict)):
        raise _not_derived('the optional plan', 'unproved legacy alternative or early bypass')
    return {'selection': selection, 'phases': phases,
            'evidence': [*guards, f'{_rel(root, target)}:{returns[0].lineno}']}


def _plan_scopes(tree: ast.Module, consts: dict, *, root=None) -> dict:
    scopes = _local_plan_scopes(tree, consts, root=root)
    delegate = _delegated_plan(root, tree) if root is not None else None
    if delegate is None:
        return scopes
    field = delegate['selection']['field']
    for phase, scope in scopes.items():
        cases = scope.get('selection', {}).get('cases', [])
        if any(case['values'].get(field) for case in cases) and phase not in delegate['phases']:
            raise _not_derived('the optional plan', 'early delegate omits enabled phase ' + phase)
    for phase in delegate['phases']:
        if phase not in scopes:
            scopes[phase] = {'conditions': delegate['selection'].get('conditions'),
                             'selection': delegate['selection']}
        scopes[phase]['delegated_plan'] = delegate
    return scopes


def _imported_target(call, bindings: dict):
    if isinstance(call.func, ast.Name):
        return bindings.get(call.func.id)
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        bound = bindings.get(call.func.value.id)
        if bound and bound[1] is None:
            return bound[0], call.func.attr
    return None


def _require_followup_binding(path: str, tree, fn, call) -> None:
    """An import must be visible, unique and unshadowed at this actual call.

    The broad discovery import map deliberately includes every function. This
    narrower derivation must not borrow another function's local import.
    """
    name = call.id if isinstance(call, ast.Name) else (call.func.id if isinstance(call.func, ast.Name) else call.func.value.id)
    fail = lambda: _not_derived("the follow-up turns", f"ambiguous import binding `{name}` at {path}:{call.lineno}")
    parents = _parents(tree)
    imports = []
    for n in ast.walk(tree):
        if not isinstance(n, (ast.Import, ast.ImportFrom)) or not any(
                (a.asname or a.name.split(".")[0]) == name for a in n.names):
            continue
        owner = parents[id(n)]
        if owner is tree:
            imports.append(n)
        else:
            cur = owner
            while cur is not tree and not isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                cur = parents[id(cur)]
            if cur is fn:
                block = _block_of(n, parents)
                after = block[block.index(n) + 1:]
                if any(call is x for stmt in after for x in ast.walk(stmt)):
                    imports.append(n)
                else:
                    raise fail()
    if len(imports) != 1 or name in _params(fn):
        raise fail()
    if any(isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del))
           for n in ast.walk(fn)):
        raise fail()
    if any(not isinstance(n, ast.alias) and _rebinding(n, name, fn) for n in ast.walk(fn)):
        raise fail()
    if any(isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del))
           and any(isinstance(x, ast.Name) and x.id == name for x in ast.walk(n.value))
           for n in ast.walk(fn)):
        raise fail()
    # Global rebinding after an import is equally ambiguous. Do not confuse a
    # same-spelled local in some unrelated function with a global assignment.
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if stmt.name == name:
                raise fail()
        elif not isinstance(stmt, (ast.Import, ast.ImportFrom)) and any(
                isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, (ast.Store, ast.Del))
                for n in ast.walk(stmt)):
            raise fail()


def _optional_guard_evidence(fn, call, selection: dict, path: str) -> list[str]:
    """Require a positive exact opt-in guard, retaining branch polarity."""
    field = selection["field"]
    protected = {f"spec.{field}"}
    if selection.get('cases'):
        protected |= {f'spec.{name}' for case in selection['cases'] for name in case['values']}
        protected |= {'spec.render_version', 'spec.runtime', 'spec.is_agentic'}
    if selection.get("conditions") is not None:
        protected.add("spec.condition")
    parents, cur, evidence = _parents(fn), call, []
    if "spec" not in _params(fn) or any((isinstance(n, ast.Name) and n.id == "spec" and isinstance(n.ctx, (ast.Store, ast.Del)))
            or (isinstance(n, ast.Attribute) and ast.unparse(n) in protected
               and isinstance(n.ctx, (ast.Store, ast.Del))) for n in ast.walk(fn)):
        raise _not_derived("which conditions make a follow-up turn", "the optional spec is reassigned")
    while id(cur) in parents:
        par = parents[id(cur)]
        if isinstance(par, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and par is not fn:
            raise _not_derived("the follow-up turns", "a nested function's call is not a direct helper call")
        if isinstance(par, (ast.If, ast.IfExp, ast.While)) and cur is not par.test:
            attributes = [n for n in ast.walk(par.test) if isinstance(n, ast.Attribute)
                          and isinstance(n.value, ast.Name) and n.value.id == "spec"]
            if attributes:
                positive = cur is par.body if isinstance(par, ast.IfExp) else any(cur is s for s in par.body)
                if not (isinstance(par, ast.If) and positive and ast.unparse(par.test) == f"spec.{field}"):
                    raise _not_derived("which conditions make a follow-up turn",
                                       f"unsupported optional call guard at {path}:{par.lineno}")
                evidence.append(f"{path}:{par.lineno}")
        cur = par
    return evidence


def _helper_replacement(caller, entry, selection, funcs, wrappers):
    """A positive optional helper replacing one loop phase's normal call."""
    parents = _parents(caller)
    path, node = [], entry
    while id(node) in parents:
        node = parents[id(node)]; path.append(node)
    axis = next((n for n in path if isinstance(n, ast.If)
                 and ast.unparse(n.test) == 'spec.' + selection['field']), None)
    if axis is None or not axis.orelse:
        return None
    phase_guard = next((n for n in path if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
        and len(n.test.ops) == 1 and isinstance(n.test.ops[0], ast.Eq)
        and isinstance(n.test.left, ast.Name) and isinstance(n.test.comparators[0], ast.Constant)
        and type(n.test.comparators[0].value) is str and any(axis is x for stmt in n.body for x in ast.walk(stmt))), None)
    if phase_guard is None:
        raise _not_derived('the selected phase replacement', 'optional alternative has no positive loop-phase equality')
    variable, phase = phase_guard.test.left.id, phase_guard.test.comparators[0].value
    if not any(isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == variable
               and isinstance(n.iter, ast.Name) and n.iter.id == 'PHASES' for n in path):
        raise _not_derived('the selected phase replacement', 'phase is not the actual PHASES loop variable')
    calls = [n for stmt in axis.orelse for n in ast.walk(stmt) if isinstance(n, ast.Call)]
    if len(calls) != 1 or not isinstance(calls[0].func, ast.Name) or calls[0].func.id not in funcs:
        raise _not_derived('the selected phase replacement', 'ordinary alternative is not one known runner function')
    call = calls[0]; ordinary = funcs[call.func.id]
    if not (call.args and isinstance(call.args[0], ast.Name) and call.args[0].id == 'spec'
            and len(call.args) > 1 and isinstance(call.args[1], ast.Name) and call.args[1].id == variable
            and any(isinstance(n, ast.Call) and _attr_or_name(n.func) in wrappers for n in ast.walk(ordinary))):
        raise _not_derived('the selected phase replacement', 'ordinary alternative is not the bound model phase')
    return {'phase': phase, 'evidence': [f'api_runner.py:{phase_guard.lineno}', f'api_runner.py:{axis.lineno}',
                                       f'api_runner.py:{call.lineno}']}


def _selection_text(selection):
    if 'cases' in selection:
        return ' OR '.join('(' + ', '.join(f'{key}={value}' for key, value in case['values'].items())
            + f"; runtime {case['runtime']}; renderer {_span(case['renderers'])}; conditions "
            + ', '.join(case['conditions']) + ')' for case in selection['cases'])
    return (f"{selection['field']} in {selection['enabled_values']}, runtime {selection['runtime']}, "
            f"renderer {_span(selection['renderers'])}")


def _helper_followups(root: Path, tree, funcs: dict, wrappers: set[str], scopes: dict) -> dict:
    """Direct imported helper calls, found through the runner's import closure.

    Resolve the wrapper alias to this runner, then read the helper's actual
    phase. Unsupported indirection fails instead of silently dropping a turn.
    """
    runner = _resolved(root / RUNNER)
    runner_bindings = _bindings(root, runner, tree, {})
    out = {}
    for path in _package_closure(root, ["data_sheets_schema.api_runner"]):
        if _resolved(path) == runner:
            continue
        helper_tree = _tree(path)
        bindings = _bindings(root, path, helper_tree, {})
        helper_funcs = {n.name: n for n in helper_tree.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for name, fn in helper_funcs.items():
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call):
                    continue
                target = _imported_target(call, bindings)
                candidate = _attr_or_name(call.func) in wrappers or (target and target[0] == runner
                                                                    and target[1] in wrappers)
                if not candidate:
                    continue
                rel = _rel(root, path)
                if not target or target[0] != runner or target[1] not in wrappers:
                    raise _not_derived("the follow-up turns", f"unresolved phase wrapper at {rel}:{call.lineno}")
                _require_followup_binding(rel, helper_tree, fn, call)
                passed_spec = _call_arg(call, funcs[target[1]], "spec")
                if not isinstance(passed_spec, ast.Name) or passed_spec.id != "spec":
                    raise _not_derived("the follow-up turns", "helper wrapper receives another spec")
                arg = _call_arg(call, funcs[target[1]], "phase")
                if arg is None:
                    raise _not_derived("the follow-up turns", f"helper call at {rel}:{call.lineno} names no phase")
                constants = _module_constants(path)
                values = ({_literal_phase(root, path, helper_tree, fn, arg)}
                          if isinstance(arg, ast.Name) and arg.id in constants else
                          _phase_names(arg, fn, helper_funcs, constants))
                entries = [(caller, c) for caller in funcs.values() for c in ast.walk(caller)
                           if isinstance(c, ast.Call) and _imported_target(c, runner_bindings) == (_resolved(path), name)]
                if not entries:
                    raise _not_derived("the follow-up turns", f"{rel}:{name} has no direct imported runner caller")
                for phase in values:
                    selection = scopes.get(phase, {}).get("selection")
                    if selection is None:
                        raise _not_derived("which conditions make a follow-up turn",
                                           f"helper phase `{phase}` has no matching optional conditional_calls entry")
                    # Inspect the helper's own enclosing guards too; they cannot
                    # secretly narrow condition/runtime selection from the plan.
                    _optional_guard_evidence(fn, call, selection, rel)
                    via = []
                    for caller, entry in entries:
                        _require_followup_binding("api_runner.py", tree, caller, entry)
                        passed_spec = _call_arg(entry, fn, "spec")
                        if not isinstance(passed_spec, ast.Name) or passed_spec.id != "spec":
                            raise _not_derived("the follow-up turns", "helper entry receives another spec")
                        guards = _optional_guard_evidence(caller, entry, selection, "api_runner.py")
                        if not guards:
                            raise _not_derived("which conditions make a follow-up turn",
                                               f"helper phase `{phase}` has an unguarded runner caller")
                        replacement = _helper_replacement(caller, entry, selection, funcs, wrappers)
                        via.append({"call": f"api_runner.py:{entry.lineno}", "guards": guards,
                                    **({'replacement': replacement} if replacement else {})})
                    row = out.setdefault(phase, {"calls": [], "conditions": scopes[phase]["conditions"],
                                                "selection": selection, "via": [],
                                                "basis": "per plan() and validated opt-in helper call path"})
                    if scopes[phase].get('delegated_plan'):
                        row['delegated_plan'] = scopes[phase]['delegated_plan']
                    row["calls"].append(f"{rel}:{call.lineno}")
                    row["via"].extend(via)
    return out


def derive_followups(tree: ast.Module, phases: list[str], consts: dict, *, root: Path | None = None) -> dict:
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
    scopes = _plan_scopes(tree, consts, root=root)
    turns = {}
    for turn, sites in sorted(calls.items()):
        if turn == "PHASES" or turn in phases:
            continue
        if turn in scopes:
            if "selection" in scopes[turn]:
                raise _not_derived("the follow-up turns", "optional local wrapper calls need a derived call path")
            scope, basis = scopes[turn]["conditions"], "per plan()'s conditional_calls"
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
    if root is not None:
        turns.update(_helper_followups(root, tree, funcs, wrappers, scopes))
    missing = sorted(t for t, scope in scopes.items() if "selection" in scope and t not in turns)
    if missing:
        raise _not_derived("the follow-up turns", "planned optional turns have no derived helper call: " + ", ".join(missing))
    return turns


# A deliberately closed string-template shape. Text constants are read from
# the source being scanned; this skeleton proves which sections it retains.
# This is not execution of the production adapter or its imports.
_TEMPLATE_SELECTION_SHAPE = '''
markers = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j')
positions = []
for marker in markers:
    if body.count(marker) != 1:
        raise ValueError(f'section {marker!r}')
    positions.append(body.index(marker))
if positions != sorted(positions):
    raise ValueError('order')
declarations = body[positions[1]:positions[2]].strip().replace(markers[1], 'label', 1)
header = body[positions[3]:positions[4]].strip().replace('old', 'new').replace('old', 'new')
rules = body[positions[8]:positions[9]].strip()
ending = body[positions[9]:].strip()
if ending != 'expected':
    raise ValueError('ending')
return policy_text(version=version) + '\\n\\n' + declarations + '\\n\\n' + header + '\\n\\n' + rules + 'return'
'''


def _template_shape(statements):
    class TextShape(ast.NodeTransformer):
        def visit_Constant(self, node):
            return ast.copy_location(ast.Constant(value='<text>'), node) if type(node.value) is str else node
    copied = ast.parse('\n'.join(ast.unparse(n) for n in statements))
    return ast.dump(TextShape().visit(copied), include_attributes=False)


def _selected_template(root, tree, selection, body):
    """Derive the selected base text from one proven section-selection adapter.

    Only inert string slicing/concatenation/replacement is evaluated. No import,
    production function, registration, environment, or generated record runs.
    Unknown call/control/template shapes refuse instead of claiming raw prompt
    references survive an opt-in adaptation.
    """
    fail = lambda why: _not_derived('the selected prompt adaptation', why)
    fn = _function(tree, 'resolve_prompt')
    if fn is None:
        raise fail('resolve_prompt is missing')
    statements = [n for n in fn.body if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)]
    # A standalone legacy adapter fixture need not define an executor. Without
    # one, no new branch may be skipped; full api_meaning still requires it.
    early = _early_axis_refusal(tree) if _function(tree, 'execute') is not None else {}
    if early and statements and isinstance(statements[0], ast.If):
        expected = ast.parse(f"getattr(spec, {early['field']!r}, 0) or spec.render_version == {early['renderer']}", mode='eval').body
        cases = selection.get('cases', [])
        guard = statements[0]
        # This branch is unreachable on each selected API case: the early
        # execute refusal fixes its axis to zero, and no selected renderer is
        # the refused native renderer. Its exact instruction delegate is
        # separately reported; no native prompt is adapted as an API prompt.
        if (ast.dump(guard.test) == ast.dump(expected) and not guard.orelse and cases
                and all(case.get('renderers') and early['renderer'] not in case['renderers']
                        and case.get('values', {}).get(early['field'], 0) == 0 for case in cases)
                and [ast.dump(n) for n in guard.body] == [ast.dump(n) for n in
                     ast.parse('from .native_shared_render import instruction\nreturn instruction(spec)').body]):
            statements = statements[1:]
    if len(statements) < 2 or ast.unparse(statements[0]) != 'body = prompt_body(spec.base_prompt)':
        raise fail('base prompt does not enter an unchanged body')
    branch = statements[1]
    if (not isinstance(branch, ast.If) or not isinstance(branch.test, ast.Attribute)
            or not isinstance(branch.test.value, ast.Name) or branch.test.value.id != 'spec'
            or branch.orelse or len(branch.body) != 2 or not isinstance(branch.body[0], ast.ImportFrom)
            or not isinstance(branch.body[1], ast.Assign) or len(branch.body[1].targets) != 1
            or ast.unparse(branch.body[1].targets[0]) != 'body'):
        raise fail('expected direct positive import and body adaptation')
    versions = {case['values'].get(branch.test.attr) for case in selection.get('cases', [])}
    if len(versions) != 1 or None in versions or 0 in versions:
        raise fail('adapter is not required by every correlated selected case')
    version = next(iter(versions)); call = branch.body[1].value
    if (not isinstance(call, ast.Call) or len(call.args) != 1 or ast.unparse(call.args[0]) != 'body'
            or len(call.keywords) != 1 or call.keywords[0].arg != 'version'
            or ast.dump(call.keywords[0].value) != ast.dump(branch.test)):
        raise fail('adapter receives changed body/version')
    _require_followup_binding(RUNNER, tree, fn, call)
    target = _imported_target(call, _bindings(root, _resolved(root / RUNNER), tree, {}))
    if target is None or target[1] is None:
        raise fail('adapter is not one imported function')
    path, name = target; adapter_tree = _tree(path); adapter = _function(adapter_tree, name)
    if adapter is None or sum(isinstance(n, ast.FunctionDef) and n.name == name for n in adapter_tree.body) != 1:
        raise fail('adapter definition is missing or ambiguous')
    if any(isinstance(n, ast.Name) and n.id in {name, 'policy_text'} and isinstance(n.ctx, (ast.Store, ast.Del))
           for statement in adapter_tree.body if not isinstance(statement, (ast.FunctionDef, ast.ClassDef))
           for n in ast.walk(statement)):
        raise fail('adapter/policy binding is reassigned')
    code = [n for n in adapter.body if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)]
    if _template_shape(code) != _template_shape(ast.parse(_TEMPLATE_SELECTION_SHAPE).body):
        raise fail('unsupported section-selection shape')
    policy = _function(adapter_tree, 'policy_text')
    if policy is None or sum(isinstance(n, ast.FunctionDef) and n.name == 'policy_text' for n in adapter_tree.body) != 1:
        raise fail('policy text binding is ambiguous')
    if (policy.args.posonlyargs or policy.args.args or policy.args.vararg or policy.args.kwarg
            or [arg.arg for arg in policy.args.kwonlyargs] != ['version']
            or any(isinstance(n, ast.Name) and n.id == 'version' and isinstance(n.ctx, (ast.Store, ast.Del))
                   for n in ast.walk(policy))):
        raise fail('policy version is not the unchanged keyword parameter')
    if adapter.decorator_list or policy.decorator_list:
        raise fail('decorated template/policy function is not a direct source binding')
    for binding_name, binding_fn in ((name, adapter), ('policy_text', policy)):
        for statement in adapter_tree.body:
            if statement is binding_fn:
                continue
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if statement.name == binding_name:
                    raise fail('template/policy binding is shadowed')
                continue
            if any(_rebinding(n, binding_name, binding_fn) or isinstance(n, ast.Name)
                   and n.id == binding_name and isinstance(n.ctx, (ast.Store, ast.Del))
                   for n in ast.walk(statement)):
                raise fail('template/policy binding is shadowed')
    prefix = [n for n in policy.body if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)]
    if (len(prefix) < 2 or not isinstance(prefix[0], ast.If) or prefix[0].orelse
            or len(prefix[0].body) != 1 or not isinstance(prefix[0].body[0], ast.Raise)):
        raise fail('unsupported policy version guard')
    guard = prefix[0].test
    if (not isinstance(guard, ast.BoolOp) or not isinstance(guard.op, ast.Or) or len(guard.values) != 2
            or ast.unparse(guard.values[0]) != 'type(version) is not int'
            or not isinstance(guard.values[1], ast.Compare) or len(guard.values[1].ops) != 1
            or not isinstance(guard.values[1].ops[0], ast.NotIn)
            or ast.unparse(guard.values[1].left) != 'version'):
        raise fail('unsupported policy version guard')
    try:
        domain = ast.literal_eval(guard.values[1].comparators[0])
    except (ValueError, TypeError):
        raise fail('policy version domain is not literal')
    if not isinstance(domain, tuple) or any(type(n) is not int for n in domain) or version not in domain:
        raise fail('selected policy version is not admitted')
    route = prefix[1]
    if (not isinstance(route, ast.If) or route.orelse
            or len(route.body) != 2 or not isinstance(route.body[0], ast.ImportFrom)
            or not isinstance(route.body[1], ast.Return)):
        raise fail('selected policy is not the direct captured-asset route')
    expression = route.body[1].value
    old_expression = "captured_assets()[API_POLICY].decode('utf-8').split('## Prompt body', 1)[1].strip()"
    if ast.unparse(route.test) == f'version == {version}' and ast.unparse(expression) == old_expression:
        asset_name = 'API_POLICY'
    elif (isinstance(route.test, ast.Compare) and ast.unparse(route.test.left) == 'version'
          and len(route.test.ops) == 1 and isinstance(route.test.ops[0], ast.In)):
        try:
            selected_versions = ast.literal_eval(route.test.comparators[0])
        except (ValueError, TypeError):
            raise fail('selected policy versions are not literal')
        if (type(selected_versions) is not tuple or len(selected_versions) != 2
                or any(type(v) is not int for v in selected_versions)
                or len(set(selected_versions)) != 2 or version not in selected_versions
                or not set(selected_versions) < set(domain)):
            raise fail('selected policy versions are not a closed subset')
        first, second = selected_versions
        expected = (f"captured_assets(version=version - 1)[API_POLICY if version == {first} else "
                    "ROUTING_API_POLICY].decode('utf-8').split('## Prompt body', 1)[1].strip()")
        if ast.dump(expression) != ast.dump(ast.parse(expected, mode='eval').body):
            raise fail('unsupported captured policy expression')
        asset_name = 'API_POLICY' if version == first else 'ROUTING_API_POLICY'
    else:
        raise fail('unsupported captured policy expression')
    names = [n for n in ast.walk(expression) if isinstance(n, ast.Name)]
    for used in names:
        if used.id != 'version':
            _require_followup_binding(_rel(root, path), adapter_tree, policy, used)
    asset_node = next(n for n in names if n.id == asset_name)
    asset = _literal_phase(root, path, adapter_tree, policy, asset_node)
    policy_bindings = _bindings(root, path, adapter_tree, {})
    if (policy_bindings.get('captured_assets', (None,))[0] != policy_bindings.get(asset_name, (None,))[0]):
        raise fail('policy loader and asset have different source authorities')
    asset_path = _resolved(root / asset)
    if _resolved(root) not in asset_path.parents or not asset_path.is_file():
        raise fail('captured policy asset is outside the source tree or missing')
    policy_raw = asset_path.read_text(encoding='utf-8')
    if policy_raw.count('## Prompt body') != 1:
        raise fail('policy body marker is not unique')
    policy_body = policy_raw.split('## Prompt body', 1)[1].strip()
    try:
        markers = ast.literal_eval(code[0].value)
        if any(type(marker) is not str or body.count(marker) != 1 for marker in markers):
            raise fail('prompt section marker is missing or repeated')
        positions = [body.index(marker) for marker in markers]
        if positions != sorted(positions):
            raise fail('prompt sections are reordered')
        values = {'body': body, 'markers': markers, 'positions': positions}
        def text_expr(n):
            if isinstance(n, ast.Constant) and type(n.value) in (str, int):
                return n.value
            if isinstance(n, ast.Name) and n.id in values:
                return values[n.id]
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                return text_expr(n.left) + text_expr(n.right)
            if isinstance(n, ast.Subscript):
                index = n.slice
                if isinstance(index, ast.Slice):
                    index = slice(*(text_expr(part) if part is not None else None
                                    for part in (index.lower, index.upper, index.step)))
                else:
                    index = text_expr(index)
                return text_expr(n.value)[index]
            if isinstance(n, ast.Call) and ast.unparse(n) == 'policy_text(version=version)':
                return policy_body
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and not n.keywords:
                value = text_expr(n.func.value); args = [text_expr(arg) for arg in n.args]
                if type(value) is str and n.func.attr in ('strip', 'replace'):
                    return getattr(value, n.func.attr)(*args)
            raise fail('unsupported inert string expression')
        for statement in code[4:8]:
            values[statement.targets[0].id] = text_expr(statement.value)
        if values['ending'] != ast.literal_eval(code[8].test.comparators[0]):
            raise fail('completion instruction changed')
        adapted = text_expr(code[9].value)
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise fail('unreadable selected template: ' + str(exc)) from exc
    return adapted, {'field': branch.test.attr, 'version': version, 'policy_asset': asset,
                     'basis': 'Adapted base prompt and selected policy, before runtime substitutions and request additions.',
                     'evidence': [f'{RUNNER}:{call.lineno}', f'{_rel(root, path)}:{adapter.lineno}',
                                  f'{_rel(root, path)}:{route.lineno}', asset]}


def _selected_request_additions(root, tree, selection):
    """Name actual guarded text-builder calls without guessing their output size."""
    fn = _function(tree, 'build_phase'); additions = []
    for branch in fn.body:
        if not isinstance(branch, ast.If) or ast.unparse(branch.test) != 'spec.' + selection['field']:
            continue
        for node in ast.walk(branch):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant) or key.value != 'text' or not isinstance(value, ast.Call):
                    continue
                _require_followup_binding(RUNNER, tree, fn, value)
                target = _imported_target(value, _bindings(root, _resolved(root / RUNNER), tree, {}))
                if target is None or target[1] is None or not value.args or ast.unparse(value.args[0]) != 'spec':
                    raise _not_derived('selected request additions', 'unbound text builder or changed spec')
                additions.append({'builder': _rel(root, target[0]) + ':' + target[1],
                                  'call': f'{RUNNER}:{value.lineno}',
                                  'size_basis': 'Selected request text; not part of the legacy digest-only estimate.'})
    return additions


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
    followups = derive_followups(tree, phases, consts, root=root)
    native_shared = derive_native_shared_route(root, tree)
    if native_shared:
        native_shared['procedure'] = derive_native_shared_procedure(root)
    if native_shared and (native_shared['runtime'] not in cond['agentic_runtimes']
                          or native_shared['condition'] not in cond['prompts']):
        raise _not_derived('native shared runtime/condition', 'contract is outside the declared runtime/condition universe')
    gh = facts.get("github_assistant_run") or {}

    def turns_for(c, *, optional=False):
        return sorted(t for t, v in followups.items() if bool(v.get("selection")) == optional
                      and (v["conditions"] is None or c in v["conditions"]))

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
            "optional_followup_turns": turns_for(name, optional=True),
            "shape": shape_of(model_phases, turns_for(name), full_schema),
            "model_calls_minimum": len(model_phases),
            "schema_form": schema_form + (" + merged-schema reference" if whole_schema else ""),
            "prompt_hybrid": bool(refs),
            "runtime_hybrid": continuation["runtime_hybrid_possible"],
            "hybrid_reasons": hybrid,
            "prompt_body_references": refs,
            "appends": list(tuned.get("appends") or []) if name == "tuned" else [],
        }

    selected_procedures = {}
    for turn, row in followups.items():
        for via in row.get('via', []):
            replacement = via.get('replacement')
            if not replacement:
                continue
            selection = row['selection']
            field = selection['field']
            procedure = selected_procedures.setdefault(field, {'selection': selection,
                'replaced_model_phases': {}, 'model_calls_minimum': None,
                'count_basis': 'Actual record-dependent helper multiplicity; no fixed count inferred from phase families.',
                'stage_scope': 'Replacement stages belong to the selected procedure, not optional additions to its old model phase.',
                'shape': 'MULTI-PHASE', 'native_runtime': 'not admitted by this API-only selector'})
            procedure['replaced_model_phases'].setdefault(replacement['phase'], []).append(turn)
    for procedure in selected_procedures.values():
        procedure['request_additions'] = _selected_request_additions(root, tree, procedure['selection'])
        procedure['ordinary_model_phases'] = [phase for phase in model_phases
            if phase not in procedure['replaced_model_phases']]
        for name in procedure['selection'].get('conditions', []):
            # This is a separately selected procedure, not the legacy audit
            # request followed by extra optional calls.
            conditions[name]['selected_procedure'] = procedure
            conditions[name]['requires_explicit_selection'] = True
            conditions[name]['model_calls_minimum'] = None
            row = conditions[name]
            if procedure['request_additions']:
                row['schema_form'] += '; additional selected text from ' + ', '.join(
                    item['builder'] for item in procedure['request_additions']) + ' (outside the legacy digest-only estimate)'
            if row['prompt_body_references']:
                raw_body = (root / row['prompt']).read_text(encoding='utf-8').split('## Prompt body', 1)[-1]
                condition_selection = {**procedure['selection'], 'cases': [
                    case for case in procedure['selection'].get('cases', []) if name in case['conditions']]}
                adapted, adaptation = _selected_template(root, tree, condition_selection, raw_body)
                row['raw_prompt_body_references'] = row['prompt_body_references']
                row['prompt_body_references'] = sorted(_named_claude_files(adapted, claude_names))
                row['selected_template_adaptation'] = adaptation
                row['prompt_hybrid'] = bool(row['prompt_body_references'])
                row['hybrid_reasons'] = [reason for reason in row['hybrid_reasons']
                    if not reason.startswith('the prompt body tells the model to read ')]
                if row['prompt_hybrid']:
                    row['hybrid_reasons'].append('the source-derived adapted base prompt retains references to '
                        + ', '.join(row['prompt_body_references']))
            conditions[name]['optional_followup_turns'] = [turn for turn in conditions[name]['optional_followup_turns']
                if any(name in case['conditions'] and name in selected_case['conditions']
                       and all(case['values'].get(k) == v for k, v in selected_case['values'].items())
                       for case in followups[turn].get('selection', {}).get('cases', [])
                       for selected_case in procedure['selection'].get('cases', []))]

    for procedure in selected_procedures.values():
        replacement = procedure['replaced_model_phases'].get('audit')
        if replacement:
            continuation['api_path'] += ('; source-derived selected audit replacement under '
                + _selection_text(procedure['selection']) + ' uses ' + ', '.join(replacement)
                + ' instead of that ordinary builder; it does not admit native execution')

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
            why.append(f"{'the default procedure' if selected_procedures else 'each run'} makes at least {len(model_phases)} model calls ({', '.join(model_phases)})")
        else:
            why.append(f"each run makes one model call ({', '.join(model_phases)}) before any follow-up turn")
        if not full_schema:
            why.append(f"it sends the {schema_form} rather than the LinkML schema")
        every = sorted(t for t, v in followups.items() if v["conditions"] is None and not v.get("selection"))
        if every:
            why.append("every condition may add " + ", ".join(every) + " turns")
        for t, v in sorted(followups.items()):
            if v["conditions"] is not None:
                live_in = [c for c in live if c in v["conditions"]]
                why.append(f"{t} runs only under {', '.join(v['conditions'])} ("
                           + (f"of the live ones, {', '.join(live_in)}" if live_in else "no live condition") + ")")
        verdict.append(f"No live API condition ({', '.join(live)}) is monolithic: " + "; ".join(why) + ".")
    for turn, row in sorted(followups.items()):
        if row.get("selection"):
            s = row["selection"]
            verdict.append(f"Optional {turn} may run only with {_selection_text(s)}; default "
                           f"{s['default']} disables it. It is not a default-condition follow-up.")
    for field, procedure in selected_procedures.items():
        verdict.append('Selected procedure ' + _selection_text(procedure['selection'])
            + ': replaces ' + '; '.join(phase + ' with ' + ', '.join(turns)
                for phase, turns in procedure['replaced_model_phases'].items())
            + '; ordinary model phases ' + ', '.join(procedure['ordinary_model_phases'])
            + '; call count is record-dependent and not inferred from the legacy phase count. Native execution is not admitted.')
    for name, row in conditions.items():
        if row.get('selected_template_adaptation'):
            adaptation = row['selected_template_adaptation']
            verdict.append(name + ': source-proven base-template adaptation under ' + adaptation['field']
                + '=' + str(adaptation['version']) + '; raw template references ('
                + ', '.join(row['raw_prompt_body_references']) + ') are retained separately from adapted base references ('
                + (', '.join(row['prompt_body_references']) or 'none') + '). Selected policy: '
                + adaptation['policy_asset'] + '; request additions are reported separately from the legacy digest estimate.')
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
    verdict.append("The agentic runtimes " + ", ".join(cond["agentic_runtimes"]) + (" render the legacy condition " if selected_procedures else " render the same condition ")
                   + "names (one name, two procedures); a run is one or the other, not a hybrid.")
    if native_shared:
        verdict.append('Separate native selection ' + native_shared['field'] + '=1, '
            + native_shared['condition'] + ', renderer ' + str(native_shared['renderer'])
            + ': API execution and API phase construction refuse it. '
            + native_shared['cli'] + ' binds the explicit runtime before rendering. ' + native_shared['scope'])
    return {"definition": ("api = MONOLITHIC: one model call whose input is the prompt, the full LinkML "
                           "schema and the input documents concatenated with separators"),
            "phases": phases, "derived_phases": derived, "model_phases": model_phases,
            **({"selected_procedures": selected_procedures} if selected_procedures else {}),
            **({'native_shared_route': native_shared} if native_shared else {}),
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


def _model_facing_statement(f: dict) -> str:
    """The report line on which package modules write model-facing text:
    the derivation's sinks, what it found, and the cross-check with
    MODEL_FACING_MODULES in both directions (#4085)."""
    mi, mf = f["model_input"], f["model_facing_modules"]
    upstream = set(f["shared_input"])
    by_file: dict[str, int] = {}
    for w in mi["writers"]:
        rel = w.rsplit(":", 1)[0]
        if rel in upstream:
            by_file[rel] = by_file.get(rel, 0) + 1
    package = [w for w in mi["writers"] if w.rsplit(":", 1)[0] not in upstream]

    def names(xs):
        return ", ".join(f"`{x}`" for x in xs) or "none"
    return ("- Which top-level `data_sheets_schema` modules write model-facing text, derived by that data flow "
            f"(#4085) from what every `{mi['request']['class']}` the runner builds carries (the class `build_phase` "
            f"returns; its {', '.join(f'`{x}`' for x in mi['request']['text_fields'])}: "
            f"{len(mi['requests'])} constructions, {names(mi['requests'])}), from what is written to a model input "
            "(each arm's bundle, and what a playbook has the model read from `" + INPUT_TREE + "`: "
            + names(mi["model_input_files"]) + f"; {len(package)} writes, {names(package)}; and the upstream input "
            "steps' writes, " + (", ".join(f"`{k}` ({v})" for k, v in sorted(by_file.items())) or "none")
            + ") and from the controllers' sinks. A module is model-facing where the flow carries one of its own "
            "sentences there: " + names(sorted(mf["derived"])) + ". Cross-checked with the hand-kept "
            "`MODEL_FACING_MODULES`: derived and not listed: " + names(mf["derived_not_listed"])
            + "; listed and not derived (model-facing by the list alone, through a channel the flow does not read): "
            + names(mf["listed_not_derived"]) + "."
            + (" Derived outside every generation closure (no surface): " + names(mf["derived_outside_closures"]) + "."
               if mf["derived_outside_closures"] else ""))


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
          "Claude Code shows the model (a PreToolUse deny reason, and the classifier reasons that feed it), "
          "from the functions that render model text, from the runner's requests and from the model-input "
          "writes (below), where the module is not model-facing as a whole: "
          + ("; ".join(f"`{k}`: " + ", ".join(v) for k, v in f["model_text"].items()) or "none") + ".",
          _model_facing_statement(f),
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
                      else "only " + ", ".join(v["conditions"]))
                      + (f"; OPT-IN {_selection_text(v['selection'])}, "
                         f"default {v['selection']['default']}; "
                         f"selection evidence {', '.join(v['selection']['evidence'])}; "
                         f"via {', '.join(x['call'] for x in v['via'])}" if v.get("selection") else "")
                      + f", {v['basis']})"
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
    L += _table([[c, v["status"], v["role"], v["shape"], "record-dependent" if v["model_calls_minimum"] is None else v["model_calls_minimum"],
                  ", ".join(v["followup_turns"]) or "none",
                  ", ".join(v["optional_followup_turns"]) or "none",
                  "yes" if v["receipt_condition"] else "", "yes" if v["prompt_hybrid"] else "no",
                  "possible" if v["runtime_hybrid"] else "no", ", ".join(v["prompt_body_references"])]
                 for c, v in m["conditions"].items()],
                ["condition", "status", "role", "shape", "min model calls", "default follow-up turns", "opt-in turns", "receipt",
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
    if m.get('native_shared_route'):
        selected = m['native_shared_route']
        L += [f"Separate native shared route: `{selected['field']}=1`, `{selected['condition']}`, "
              f"renderer {selected['renderer']}, `{selected['runtime']}`. API execution: {selected['api_execute']}; "
              f"API phase construction: {selected['api_phase_builder']}. Offline consumer: `{selected['cli']}`. "
              + selected['scope'],
              selected['runtime_binding']['basis'],
              'Companion axes: ' + ', '.join(f'`{key}={value}`' for key,value in selected['companion_axes'].items())
              + '. Evidence: ' + ', '.join(selected['evidence']) + '.', '']
    if m.get('native_shared_route', {}).get('procedure'):
        procedure = m['native_shared_route']['procedure']
        L += [procedure['basis'], 'Required response-bearing stage roster: `'
              + procedure['protocol_responses']['formula'] + '`. Actual count and model-call count: unknown. '
              'This is not observed answer or provider accounting.', '']
        L += _table([[row['kind'], row['cardinality'], row.get('condition', row.get('requirement', ''))]
                     for row in procedure['stages']], ['selected native stage', 'required cardinality', 'basis']) + ['']
        L += [str(procedure['helper_kind_count']) + ' helper command kinds (not invocation counts): '
              + ', '.join('`' + key + '`' for key in procedure['helper_commands']) + '.',
              'Structural evidence: ' + ', '.join(procedure['evidence']) + '.',
              'Source-linked procedure descriptions; runtime enforcement is not proved by this scanner:', '']
        L += ['- ' + note['description'] + ' Source: `' + note['source'] + '`.'
              for note in procedure['procedure_notes']] + ['']
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
