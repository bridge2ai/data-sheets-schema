#!/usr/bin/env python3
"""Generation-specificity audit (#4007): deterministic, offline, stdlib + PyYAML.

Finds text and code in the D4D generation process that is specific to a
Bridge2AI Grand Challenge project (a violation), to the Bridge2AI program
(tracked) or to biomedical/clinical data (tracked), and reports what "api"
means in the code: one monolithic call, or several phases.

    python .claude/skills/d4d-generation-specificity-audit/scan.py \
        --report notes/x.md --json notes/x.json

Exit status: 0 when no gc_project hit outside an exception is model-facing or
a code branch/table in a gating surface; 1 when one is; 2 when the self-test
or the configuration fails (a scanner that cannot see is not run).

Nothing here imports the project package: the runner's tables are read with
`ast`, so the audit runs from any checkout without its dependencies and never
executes generation code.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SKILL_DIR.parents[2]
TOKENS_FILE = SKILL_DIR / "tokens.yaml"
EXCEPTIONS_FILE = SKILL_DIR / "exceptions.yaml"
NEUTRALITY_TEST = "tests/test_neutral_generation_schema.py"
CATEGORIES = ("gc_project", "bridge2ai_program", "biomedical_clinical")
TRACKED = ("bridge2ai_program", "biomedical_clinical")

APPROACHES = {
    # name: (gates the exit status, description)
    "native_agentic": (True, "Claude Code / native runtime following the d4d playbooks"),
    "api": (True, "d4d api run|batch: api_runner and its condition prompts"),
    "github_assistant": (True, "the @d4dassistant workflow and its instruction files"),
    "shared_schema": (True, "the LinkML generation schema, digest inputs, profile and manifest"),
    "deterministic": (True, "the healthsheet and RO-Crate arms that build bundles or records"),
    "legacy_monolithic": (True, "the pre-runner scripts and prompt sets (process_*.py)"),
    "shared_input": (False, "download/preprocess/concatenate, upstream of every approach"),
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


def load_tokens(root: Path, tokens_file: Path = TOKENS_FILE) -> list[Token]:
    spec = yaml.safe_load(tokens_file.read_text(encoding="utf-8"))
    imported = spec.get("imported_lists") or {}
    lists = _assigned_lists(root / NEUTRALITY_TEST, set(imported))
    missing = set(imported) - set(lists)
    if missing:
        raise ValueError(f"{NEUTRALITY_TEST} no longer defines {sorted(missing)}; "
                         "the audit's token source moved — update tokens.yaml")
    tokens, seen = [], set()

    def add(category, pattern, source):
        if category not in CATEGORIES:
            raise ValueError(f"unknown token category {category!r} for {pattern!r}")
        if (category, pattern) in seen:
            return
        seen.add((category, pattern))
        tokens.append(Token(category, pattern, source, re.compile(pattern, re.IGNORECASE)))

    for name, category in imported.items():
        for pattern in lists[name]:
            add(category, pattern, f"{NEUTRALITY_TEST}:{name}")
    for category, patterns in (spec.get("extensions") or {}).items():
        for pattern in patterns or []:
            add(category, pattern, "tokens.yaml")
    IGNORE[:] = [re.compile(p, re.IGNORECASE) for p in spec.get("ignore") or []]
    return tokens


def match_text(text: str, tokens: list[Token]) -> list[tuple[int, int, Token, str]]:
    """Non-overlapping matches; on overlap the more specific category wins."""
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


def _python_units(text: str):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for i, line in enumerate(text.splitlines(), 1):
            yield i, "unparsed", line, line
        return
    lines = text.splitlines()
    docstrings, branch, table = set(), set(), set()
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
        if isinstance(node, ast.keyword) and node.arg == "default" and _bare_token(node.value):
            table.add(id(node.value))          # argparse/click default="CHORUS"
    for node in tree.body:                      # module constants: PROJECTS = [...], ORDER = "A,B"
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            value = node.value
            elts = value.elts if isinstance(value, (ast.List, ast.Tuple, ast.Set)) else [value]
            table.update(id(e) for e in elts if _bare_token(e))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        context = ("docstring" if id(node) in docstrings else "code_branch" if id(node) in branch
                   else "code_table" if id(node) in table else "string_literal")
        value = node.value
        # one unit per physical line of the literal, so line numbers are exact
        # for the common cases (single-line literals and triple-quoted blocks)
        for offset, part in enumerate(value.split("\n")):
            lineno = node.lineno + offset if node.end_lineno != node.lineno else node.lineno
            src = lines[lineno - 1] if 0 < lineno <= len(lines) else part
            yield lineno, context, part, src
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                yield tok.start[0], "comment", tok.string, lines[tok.start[0] - 1]
    except (tokenize.TokenError, IndentationError):
        pass


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


def _exists_exact(p: Path) -> bool:
    """Existence with the exact spelling: on a case-insensitive filesystem
    `constants/PROJECTS.py` "exists" because `projects.py` does, and an
    imported constant named PROJECTS would be taken for a module."""
    try:
        return p.name in {c.name for c in p.parent.iterdir()}
    except OSError:
        return False


def _schema_closure(schema_dir: Path, root_name: str) -> list[Path]:
    seen, todo = [], [schema_dir / root_name]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        if not p.exists():
            raise FileNotFoundError(f"schema module not found: {p}")
        seen.append(p)
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for name in doc.get("imports") or []:
            if not name.startswith("linkml:"):
                todo.append(p.parent / f"{name}.yaml")
    return seen


def condition_table(root: Path) -> dict:
    """The runner's conditions, read from api_runner.py and cli/api.py by ast."""
    env = _module_constants(root / "src/data_sheets_schema/api_runner.py")
    prompts = env.get("CONDITION_PROMPTS") or {}
    if not prompts:
        raise ValueError("api_runner.CONDITION_PROMPTS could not be read")
    versions = {c: int(m.group(1)) for c in prompts if (m := re.fullmatch(r"generic_v(\d+)", c))}
    current = max(versions, key=versions.get) if versions else None
    default = "generic"
    cli = root / "src/data_sheets_schema/cli/api.py"
    for node in ast.walk(ast.parse(cli.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple) and node.value.elts and \
                isinstance(node.value.elts[0], ast.Constant) and node.value.elts[0].value in prompts \
                and isinstance(node.targets[0], ast.Tuple) and \
                any(isinstance(t, ast.Name) and t.id == "condition" for t in node.targets[0].elts):
            default = node.value.elts[0].value
    live = sorted({c for c in (current, default) if c})
    return {"prompts": prompts, "current": current, "default": default, "live": live,
            "tuned_prompt": env.get("TUNED_PROMPT"), "components": env.get("COMPONENTS"),
            "receipt_conditions": sorted(env.get("RECEIPT_CONDITIONS") or ()),
            "phases": list(env.get("PHASES") or ()),
            "derived_phases": sorted(env.get("DERIVED_PHASES") or ()),
            "core_derived": bool(env.get("CORE_DERIVED")),
            "agentic_runtimes": sorted(env.get("AGENTIC_RUNTIMES") or ())}


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

    # ---- native agentic
    commands = sorted((root / ".claude/commands").glob("d4d-*.md"))
    agents = sorted((root / ".claude/agents").glob("*.md"))
    referenced: set[str] = set()
    todo = [c for c in commands] + [root / cond["prompts"][c] for c in cond["live"]]
    while todo:
        p = todo.pop()
        if not p.exists():
            continue
        for ref in CLAUDE_REF.findall(p.read_text(encoding="utf-8")):
            if ref not in referenced:
                referenced.add(ref)
                todo.append(root / ref)
    facts["native_referenced"] = sorted(referenced)
    for p in commands:
        s.add(_rel(root, p), "native_agentic", "model_facing", "live", "d4d playbook (slash command)")
    for p in agents:
        rel = _rel(root, p)
        if rel in referenced:
            s.add(rel, "native_agentic", "model_facing", "live", "agent named by a playbook or live prompt")
        else:
            s.add(rel, "native_agentic", "exposed", "live",
                  "handed to native runs by agentic_runtime.toolchain(); no playbook names it")
    controllers = []
    for pattern in ("notes/*/native_controls/*.py", "notes/*/audit_controls/*.py",
                    "notes/claudecode_direct/*.py", "notes/*/prepare_registration.py",
                    "notes/*/native_context.py"):
        controllers += [p for p in sorted(root.glob(pattern)) if not p.name.startswith(("test_", "probe_"))]
    for p in controllers:
        s.add(_rel(root, p), "native_agentic", "run_shaping", "live", "native/direct controller")
    playbook = root / ".claude/commands/d4d-full-core.md"
    groups = sorted(set(re.findall(r"\bd4d ([a-z][\w-]*) [a-z]", playbook.read_text(encoding="utf-8"))))
    starts = ["data_sheets_schema.agentic_runtime"] + [
        f"data_sheets_schema.cli.{g.replace('-', '_')}" for g in groups
        if (src / "cli" / f"{g.replace('-', '_')}.py").exists()]
    # the package modules the controllers import (the native audit batch, #renderer 20)
    for p in controllers:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
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
    for pattern in ("notes/*/native_controls/system.md", "notes/claudecode_direct/system.md"):
        for p in sorted(root.glob(pattern)):
            s.add(_rel(root, p), "native_agentic", "model_facing", "live", "appended system prompt")
    for p in sorted((root / ".claude/agents/scripts").glob("*.py")):
        s.add(_rel(root, p), "native_agentic", "run_shaping", "live", "agent helper script")

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

    # ---- legacy monolithic
    legacy_py = sorted((root / "src/download").glob("process_*.py")) + \
        [p for p in sorted((root / "src/download").glob("*.py"))
         if re.search(r"d4d|prompt_loader", p.name) and not p.name.startswith("process_")]
    for p in legacy_py:
        s.add(_rel(root, p), "legacy_monolithic", "run_shaping", "legacy", "legacy generation script")
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


def load_exceptions(path: Path = EXCEPTIONS_FILE) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = doc.get("exceptions") or []
    for i, e in enumerate(entries):
        extra = set(e) - EXCEPTION_KEYS
        if extra:
            raise ValueError(f"exception {i}: unknown keys {sorted(extra)}")
        for key in ("path", "reason", "decision"):
            if not e.get(key):
                raise ValueError(f"exception {i}: `{key}` is required")
        if not e.get("token") and not e.get("category"):
            raise ValueError(f"exception {i}: name a `token` or a `category`")
        cats = e.get("category")
        cats = [cats] if isinstance(cats, str) else (cats or [])
        bad = set(cats) - set(CATEGORIES)
        if bad:
            raise ValueError(f"exception {i}: unknown category {sorted(bad)}")
        e["_categories"] = cats
        e["_paths"] = [e["path"]] if isinstance(e["path"], str) else list(e["path"])
        e["_contexts"] = [e["context"]] if isinstance(e.get("context"), str) else (e.get("context") or [])
        e["_token"] = re.compile(e["token"], re.IGNORECASE) if e.get("token") else None
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


def scan_file(root: Path, surface: Surface, tokens: list[Token]) -> list[dict]:
    path = root / surface.path
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return []
    hits = []
    for line, context, unit, src in units_for(path, surface.path, text):
        for _, _, tok, matched in match_text(unit, tokens):
            model_facing = surface.role == "model_facing" and context in MODEL_FACING_CONTEXTS
            hits.append({
                "path": surface.path, "line": line, "approaches": list(surface.approaches),
                "role": surface.role, "status": surface.status, "context": context,
                "category": tok.category, "match": matched, "pattern": tok.pattern,
                "model_facing": model_facing, "code": context in CODE_CONTEXTS,
                "snippet": src.strip()[:180],
            })
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


def self_test(tokens: list[Token]) -> dict:
    planted = {"gc_project": "AI-READI", "bridge2ai_program": "Bridge2AI", "biomedical_clinical": "clinical"}
    with tempfile.TemporaryDirectory(prefix="d4d-specificity-selftest-") as d:
        root = Path(d)
        (root / "seed.md").write_text(
            "# Seed\n\nRecord the AI-READI release.\nThe Bridge2AI program funds it.\n"
            "Describe the clinical cohort.\n", encoding="utf-8")
        (root / "seed.py").write_text(
            "def f(project):\n    if project == 'CHORUS':\n        return 'see fairhub'\n"
            "    # a VOICE comment\n    return {'CM4AI': 1}\n", encoding="utf-8")
        found = {}
        for name in ("seed.md", "seed.py"):
            surf = Surface(name, ["api"], "model_facing", "live", "self-test")
            found[name] = scan_file(root, surf, tokens)
    md = {(h["category"], h["match"]) for h in found["seed.md"]}
    py = {(h["context"], h["match"]) for h in found["seed.py"]}
    problems = [f"{cat}: planted {tok!r} not found" for cat, tok in planted.items() if (cat, tok) not in md]
    for want in (("code_branch", "CHORUS"), ("string_literal", "fairhub"), ("comment", "VOICE"),
                 ("code_table", "CM4AI")):
        if want not in py:
            problems.append(f"python: expected {want} in {sorted(py)}")
    md_line = {h["line"] for h in found["seed.md"] if h["match"] == "AI-READI"}
    if md_line != {3}:
        problems.append(f"line numbers: AI-READI reported at {md_line}, planted at 3")
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
# "api" meaning, derived from the code


LLM_CALL = re.compile(r"\.messages\.create\(|\.chat\.completions\.create\(|\.responses\.create\(|"
                      r"\w*agent\.run(?:_sync)?\(")


def _function(tree: ast.Module, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def api_meaning(root: Path, facts: dict) -> dict:
    runner_path = root / "src/data_sheets_schema/api_runner.py"
    runner_text = runner_path.read_text(encoding="utf-8")
    tree = ast.parse(runner_text)
    cond = facts["conditions"]
    phases = cond["phases"]
    derived = cond["derived_phases"] if cond["core_derived"] else []
    model_phases = [p for p in phases if p not in derived]

    build = _function(tree, "build_phase")
    calls = {n.attr for n in ast.walk(build) if isinstance(n, ast.Attribute)} if build else set()
    consts = [n.value for n in ast.walk(build) if isinstance(n, ast.Constant) and isinstance(n.value, str)] \
        if build else []
    schema_form = "schema digest (schema_digest.digest_text)" if "digest_text" in calls else "unknown"
    whole_schema = any("_all.yaml" in c for c in consts)
    agentic_audit_from = None
    if build:
        for node in ast.walk(build):
            if isinstance(node, ast.If):
                text = ast.unparse(node.test)
                m = re.search(r"render_version\s*>=\s*(\d+)\s+and\s+phase\s*==\s*'audit'", text)
                raises = [r for r in ast.walk(node) if isinstance(r, ast.Raise)]
                if m and raises and "batch-context" in ast.unparse(raises[0]):
                    agentic_audit_from = int(m.group(1))
    rm = re.search(r"self\.render_version = (\d+) if self\.is_agentic else (\d+)", runner_text)
    default_renderer = {"agentic": int(rm.group(1)), "api": int(rm.group(2))} if rm else {}
    funcs = sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef))
    instruction_keys: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name) and target.id == "PHASE_INSTRUCTIONS" and \
                    isinstance(node.value, ast.Dict):
                instruction_keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
    # A follow-up turn is an instruction the runner can send that is not one
    # of the PHASES, or a builder for one (build_readdress, build_repair).
    followups: dict[str, list[str]] = {}
    for key in instruction_keys:
        if key not in phases and key != "full_receipt":
            followups.setdefault(key, []).append("PHASE_INSTRUCTIONS")
    for f in funcs:
        if f.startswith("build_") and f != "build_phase":
            followups.setdefault(f[len("build_"):], []).append(f)

    conditions = {}
    for name, rel in sorted(cond["prompts"].items()):
        p = root / rel
        body = p.read_text(encoding="utf-8").split("## Prompt body", 1)[-1] if p.exists() else ""
        refs = sorted(set(CLAUDE_REF.findall(body)))
        hybrid = []
        if refs:
            hybrid.append("the prompt body tells the model to read " + ", ".join(refs)
                          + "; the API request never carries those files (an agentic-only instruction)")
        if agentic_audit_from is not None:
            hybrid.append(f"when rendered at renderer >= {agentic_audit_from} the audit phase refuses the API "
                          "path and requires the registered native audit batch (an agentic step)")
        if cond["agentic_runtimes"]:
            hybrid.append("the same condition renders for an agentic runtime (RunSpec.is_agentic): one "
                          "condition name, two procedures")
        conditions[name] = {
            "status": "live" if name in cond["live"] else "historical",
            "role": ("current generic" if name == cond["current"] else "")
                    + (" + CLI default (GitHub assistant)" if name == cond["default"] else "")
                    + ("per-project tuning: appends components/{PROJECT}.md" if name == "tuned" else ""),
            "prompt": rel,
            "receipt_condition": name in cond["receipt_conditions"],
            "tuned": name == "tuned",
            "shape": "MULTI-PHASE" if (len(model_phases) > 1 or followups) else "MONOLITHIC",
            "model_calls_minimum": len(model_phases),
            "schema_form": schema_form + (" + merged-schema reference" if whole_schema else ""),
            "hybrid": bool(refs),
            "agentic_step_when": (f"renderer >= {agentic_audit_from} (audit)"
                                  if agentic_audit_from is not None else None),
            "hybrid_reasons": hybrid,
            "prompt_body_references": refs,
            "appends": ([cond["tuned_prompt"], f"{cond['components']}/{{PROJECT}}.md"]
                        if name == "tuned" else []),
        }

    cli_env = _module_constants(root / "src/data_sheets_schema/cli/api.py")
    arms = {}
    for arm, row in sorted((cli_env.get("ARMS") or {}).items()):
        arms[arm] = {"method_dir": row[1], "bundle": row[2],
                     "shape": "MULTI-PHASE (same phase list as every condition)",
                     "manifest": row[3].replace("# Source manifest: ", "")}

    legacy = {}
    for p in sorted((root / "src/download").glob("process_*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        n_calls = len(LLM_CALL.findall(text))
        full_schema = bool(re.search(r"_all\.yaml|get_full_schema", text))
        concatenated = "concatenat" in p.name
        tools = re.findall(r"@[\w.]*\.tool(?:_plain)?\b", text)
        shape = ("MONOLITHIC" if n_calls == 1 and full_schema and concatenated and not tools else
                 "MONOLITHIC + TOOLS (hybrid)" if n_calls and full_schema and concatenated else
                 "PER-DOCUMENT" if n_calls and not concatenated else
                 "NO MODEL CALL" if not n_calls else "UNCLEAR")
        legacy[_rel(root, p)] = {"shape": shape, "model_call_sites": n_calls, "full_schema": full_schema,
                                 "concatenated_input": concatenated, "tool_decorators": len(tools)}

    gh = {}
    yml = root / ".github/workflows/d4d-agent.yml"
    if yml.exists():
        text = yml.read_text(encoding="utf-8")
        m = re.search(r"d4d api run(?:[^\n]*\\\n)*[^\n]*", text)
        block = m.group(0) if m else ""
        cm = re.search(r"--condition\s+(\S+)", block)
        gh = {"command": " ".join(block.replace("\\\n", " ").split()),
              "condition": cm.group(1) if cm else f"{cond['default']} (CLI default; no --condition)",
              "manifest": "given" if "--manifest" in block else "none passed (neutral for an external bundle)",
              "shape": conditions.get(cm.group(1) if cm else cond["default"], {}).get("shape", "unknown")}

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
    if mono_legacy:
        verdict.append("The monolithic shape (prompt + full LinkML schema + concatenated documents, one "
                       "call) survives only in legacy scripts: " + ", ".join(mono_legacy) + ".")
    hybrids = sorted(c for c in cond["live"] if conditions[c]["hybrid"])
    if hybrids:
        verdict.append("Live conditions with an agentic component or agentic-only instruction: "
                       + ", ".join(hybrids) + ".")
    return {"definition": ("api = MONOLITHIC: one model call whose input is the prompt, the full LinkML "
                           "schema and the input documents concatenated with separators"),
            "phases": phases, "derived_phases": derived, "model_phases": model_phases,
            "schema_form": schema_form, "followup_turns": followups,
            "agentic_audit_from_renderer": agentic_audit_from,
            "default_renderer": default_renderer,
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
    hits = []
    for rel in sorted(surfaces.files):
        hits.extend(scan_file(root, surfaces.files[rel], tokens))
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

    L += ["## gc_project violations", "",
          "A Grand Challenge project's name, site or identifier in model-facing text or in a code "
          "branch/table of a generation surface, with no tracked exception. Fix each: move the fact "
          "into the manifest or profile, or remove it.", ""]
    if viol:
        L += _table([[f"`{h['path']}:{h['line']}`", ",".join(h["approaches"]), h["status"], h["context"],
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
          "toolchain exposes but no playbook names, or upstream of generation.", ""]
    quiet: dict[tuple, list] = {}
    for h in hits:
        if h["category"] == "gc_project" and not h["violation"]:
            why = (f"exception #{h['exception']}" if h["exception"] is not None else
                   "exposed" if h["role"] == "exposed" else
                   "upstream" if not any(APPROACHES[a][0] for a in h["approaches"]) else h["context"])
            quiet.setdefault((h["path"], why), []).append(h)
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
    L += ["## What \"api\" means in the code", "", f"Definition checked: {m['definition']}.", ""]
    L += [f"- Phases (`api_runner.PHASES`): {', '.join(m['phases'])}; derived without a model call: "
          f"{', '.join(m['derived_phases']) or 'none'}; model phases: {', '.join(m['model_phases'])}.",
          f"- Schema sent: {m['schema_form']}.",
          f"- Follow-up turns: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in m["followup_turns"].items()),
          f"- Agentic step: the audit phase requires the registered native batch from renderer "
          f"{m['agentic_audit_from_renderer']} (default renderer when none is registered: "
          f"{m['default_renderer'].get('api')} for the API runtime, {m['default_renderer'].get('agentic')} "
          f"for an agentic one); agentic runtimes that "
          f"render the same conditions: {', '.join(m['agentic_runtimes'])}.", ""]
    L += _table([[c, v["status"], v["role"].strip(" +") or "", v["shape"], v["model_calls_minimum"],
                  "yes" if v["receipt_condition"] else "", "yes" if v["hybrid"] else "no",
                  v["agentic_step_when"] or "", ", ".join(v["prompt_body_references"])]
                 for c, v in m["conditions"].items()],
                ["condition", "status", "role", "shape", "min model calls", "receipt",
                 "agentic-only instruction", "agentic step", "playbook files the body names"]) + [""]
    L += ["Why a condition is marked hybrid: " + "; ".join(next(iter(m["conditions"].values()))["hybrid_reasons"])
          + ".", ""] if m["conditions"] else []
    L += _table([[a, v["method_dir"], v["bundle"], v["shape"]] for a, v in m["arms"].items()],
                ["arm", "method dir", "bundle", "shape"]) + [""]
    L += _table([[f"`{p}`", v["shape"], v["model_call_sites"], v["full_schema"], v["concatenated_input"],
                  v["tool_decorators"]] for p, v in m["legacy"].items()],
                ["legacy script", "shape", "call sites", "full schema", "concatenated input", "tools"]) + [""]
    gh = m["github_assistant"]
    if gh:
        L += [f"GitHub assistant: `{gh['command']}` — condition {gh['condition']}; manifest "
              f"{gh['manifest']}; shape {gh['shape']}.", ""]
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
    if args.self_test_only:
        st = self_test(load_tokens(root, args.tokens))
        print(json.dumps(st, indent=2))
        return 0 if st["passed"] else 2
    try:
        result = run(root, args.tokens, args.exceptions)
    except (ValueError, FileNotFoundError, yaml.YAMLError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    report = args.report or Path(tempfile.mkdtemp(prefix="d4d-specificity-")) / "generation_specificity_audit.md"
    js = args.json or report.with_suffix(".json")
    report.parent.mkdir(parents=True, exist_ok=True)
    js.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_markdown(result), encoding="utf-8")
    payload = result if args.full_json else summarize(result)
    js.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"report: {report}\njson:   {js}")
    print(f"violations: {len(result.get('violations', []))}; exit {result['exit']}")
    return result["exit"]


if __name__ == "__main__":
    sys.exit(main())
