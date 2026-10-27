"""The generation-specificity audit skill runs and can see (#4007).

`.claude/skills/d4d-generation-specificity-audit/scan.py` finds Grand
Challenge project, Bridge2AI program and biomedical/clinical specificity in
the generation surfaces of every approach, and reports what "api" means in
the code. These tests pin that the scanner is not blind and that what it
reports is derived from the code that decides it:

- the self-test plants one token per category and checks each planted item's
  context and line, and a token planted in a copy of a real surface, under
  the role `discover()` gives that surface, is reported as a violation;
- project-keyed tables, defaults and keys in run-shaping code gate (#4024);
- discovery finds every model client, controller, launcher, named file and
  arm from the code rather than a glob list, follows text a model receives
  by data flow, and classes CLAUDE.md under interactive sessions (#4023,
  #4054);
- it follows the imports of every script a text runs and every CLI group it
  runs, the descriptions a session lists, the YAML comments a playbook's
  Read returns, and the code in run-shaping workflows, configs and shell
  scripts (#4091); a Python file that does not parse stops the scan, whether
  registered runs load the session is read from each launch's argv, and a
  non-literal --condition is not derived (#4092); an assistant instruction
  file is a surface only where something loads it, and a controller module
  runs as a script only where something runs it (#4093);
- an `or` default, a wrapped value, a positional argument, a regex or glob
  test and a yielded value gate as code; a controller's own `__main__` block
  that launches a run or runs a command-line interface makes it run; the
  reason a PreToolUse hook gives a native run's model for a denial, and the
  classifier reasons that feed it, are model text; run-shaping JSON and a
  workflow's `contains(fromJSON(...))` are code (#4130);
- only `--safe-mode` switches the session descriptions off (`--bare` the
  memory and the hooks), a flag list something can shorten is not shown to
  carry a flag, a `--system-prompt-file` launch is a launch, the project
  settings and their hooks are found, and the skill's own description has a
  recorded reason (#4131);
- an argv bound by an annotated assignment, or held by an attribute or an
  item, is read for what shortens it; a hook field set by item assignment,
  `+=` or `.setdefault()`, or from a local, is model text with the
  classifier reasons that feed it; a JSON hook command with escapes is read
  as shell (#4142);
- a launch is shown to pass a flag only where the flag is a literal element
  of the argv list it hands over as built: a concatenation (Codex's
  reproduction, with a removal or without one), a starred element, a value
  wrapped in a call and a holder used any other way than to hand the list
  on are not shown, so no registered launch of this checkout is; and the
  constants a model-text constant is built from are model text too (#4156);
- a holder is shown only where its one binding comes before every other use
  of it in the same statement list and a name holder is not a parameter
  (Codex's `go(argv, enabled)`, an existing attribute or item bound
  conditionally or used first); and a method call on a marked constant is a
  write of it wherever a top-level statement makes it, in an assignment's
  value (Codex's `setdefault`, an assigned `append`), an argument or a
  condition, with its arguments followed (#4166);
- which top-level package modules write model-facing text is derived by
  data flow from the runner's requests, the model-input writes and the
  controllers' sinks, and the hand-kept MODEL_FACING_MODULES is checked
  against it in both directions: a project name in a new module whose
  constant `build_phase` sends, or in one the healthsheet bundle is built
  from, gates, and does not when the derivation is off (#4085);
- the "api" section's derivations agree with what the runtime does, read
  their code in any spelling, and fail loudly rather than fall back (#4022,
  #4025, #4055, #4057, #4058);
- a violation is exit 1, a clean scan 0, and a scan that did not happen 2
  (#4027, #4057, #4058).

None of these tests walks the record corpus (`data/d4d_concatenated`), so
none is marked `corpus` (#4027).
"""
from __future__ import annotations

import ast
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import unittest
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "d4d-generation-specificity-audit"
#: The trees discovery must read, written out here rather than read from the
#: scanner, so a scanner that drops one fails the cross-check (#4054).
DISCOVERY_TREES = ("src", "notes", "scripts")
#: Where a violation in an interactive-session surface of this checkout
#: gates (#4156): no registered native launch is shown to pass `--safe-mode`
#: or `--bare`, since each takes its flags from a starred module constant or
#: record field, which the sound rule does not follow
#: (`test_no_registered_launch_is_shown_to_switch_the_session_off` pins
#: that), so every session surface is a run_controllers surface too.
SESSION_GATES = ["interactive_session", "run_controllers"]


def _load_scanner():
    spec = importlib.util.spec_from_file_location("d4d_specificity_scan", SKILL / "scan.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module          # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


scan = _load_scanner()


@lru_cache(maxsize=None)
def _discovered():
    """discover() once per test process (read-only for every caller)."""
    return scan.discover(ROOT)


@lru_cache(maxsize=None)
def _meaning():
    return scan.api_meaning(ROOT, _discovered()[1])


@lru_cache(maxsize=None)
def _full_run():
    return scan.run(ROOT)


@lru_cache(maxsize=None)
def _tokens():
    return tuple(scan.load_tokens(ROOT))


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _scan_text(rel: str, text: str, surface) -> list[dict]:
    """Scan `text` as the file `rel` under `surface` in a scratch root, with
    every hit judged as if no exception applied."""
    with tempfile.TemporaryDirectory() as d:
        _write(Path(d) / rel, text)
        hits = scan.scan_file(Path(d), surface, list(_tokens()))
    for h in hits:
        h["exception"] = None
        h["violation"] = scan.is_violation(h)
    return hits


def _parsed(root: Path, *tops: str) -> dict:
    return {p.resolve(): scan._parse(p) for top in tops for p in (root / top).rglob("*.py")}


def _plant(rel: str, line: str, after: str | None = None, surface=None):
    """Plant a line in a copy of a real surface and scan it under the role
    discover() gives that surface, or under `surface` (#4026): a
    misclassified real surface fails the tests that use this. With `after`,
    the line goes right after the first line that starts with it; otherwise
    at the end. Returns (the planted line's hits, every hit)."""
    surface = surface or _discovered()[0].files[rel]
    text = (ROOT / rel).read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    lines = text.splitlines()
    if after is None:
        at = len(lines)
    else:
        at = next(i for i, x in enumerate(lines, 1) if x.lstrip().startswith(after))
    new = "\n".join(lines[:at] + line.split("\n") + lines[at:]) + "\n"
    first, last = at + 1, at + len(line.split("\n"))
    hits = _scan_text(rel, new, surface)
    return [h for h in hits if first <= h["line"] <= last], hits


#: Launch rows a mocked `launch_flags` returns in place of this checkout's,
#: whose four launches are all "not shown" (#4156): one passing no flag, one
#: passing `--bare` alone, one shown to pass `--safe-mode`.
UNSAFE_LAUNCH = {"site": "notes/exp_4092/launch.py:9 --system-prompt", "carries": False,
                 "evidence": ["notes/exp_4092/launch.py:8 no element of the argv list is the literal `--safe-mode`"],
                 "memory_off": False,
                 "memory_evidence": ["notes/exp_4092/launch.py:8 no element of the argv list is the literal "
                                     "`--safe-mode` or `--bare`"]}
BARE_LAUNCH = {"site": "notes/exp_4131/launch.py:9 --system-prompt", "carries": False,
               "evidence": ["notes/exp_4131/launch.py:8 no element of the argv list is the literal `--safe-mode`"],
               "memory_off": True, "memory_evidence": ["notes/exp_4131/launch.py:8 --bare"]}
SAFE_LAUNCH = {"site": "notes/exp_4156/launch.py:9 --system-prompt", "carries": True,
               "evidence": ["notes/exp_4156/launch.py:8 --safe-mode"], "memory_off": True,
               "memory_evidence": ["notes/exp_4156/launch.py:8 --safe-mode"]}


def _with_launches(rows: list):
    """A `launch_flags` side effect that returns `rows` in place of the
    launches discovery reads."""
    return mock.patch.object(scan, "launch_flags", side_effect=lambda *a, **k: [dict(r) for r in rows])


@lru_cache(maxsize=None)
def _discovered_with_a_loading_workflow_and_an_unsafe_launch():
    """discover() of this checkout with two things it does not do today
    (#4092, #4093): the @d4dassistant workflow names an instruction file
    (d4d_assistant_edit.md), and its one registered native launch passes
    no --safe-mode. Computed once; the mocks are gone when it returns."""
    workflow = (ROOT / ".github/workflows/d4d-agent.yml").read_text(encoding="utf-8")
    real_named = scan._named_files

    def named(root, text, claude_names):
        got = real_named(root, text, claude_names)
        return {**got, ".github/workflows/d4d_assistant_edit.md": False} if text == workflow else got

    with mock.patch.object(scan, "_named_files", side_effect=named), _with_launches([UNSAFE_LAUNCH]):
        return scan.discover(ROOT)


@lru_cache(maxsize=None)
def _discovered_with_a_bare_launch():
    """discover() of this checkout whose registered native launches are one
    shown to pass `--safe-mode` and one that passes `--bare` and not
    `--safe-mode` (#4131). Computed once."""
    with _with_launches([SAFE_LAUNCH, BARE_LAUNCH]):
        return scan.discover(ROOT)


@lru_cache(maxsize=None)
def _discovered_with_every_launch_shown():
    """discover() of this checkout whose registered native launches are all
    shown to pass `--safe-mode` (#4156). Computed once."""
    with _with_launches([SAFE_LAUNCH]):
        return scan.discover(ROOT)


#: The registered native controls two equivalent rewrites edit (#4142).
NATIVE_CONTROL = "notes/matched_cborg_2026-09-13/native_controls/native_control.py"
AUDIT_NATIVE = "notes/matched_cborg_2026-09-13/audit_controls/native.py"
HOOK_OUTPUT_DICT = ("    return {} if classification == 'prescribed' else {'hookSpecificOutput': {\n"
                    "        'hookEventName': CONTRACT['event'], 'permissionDecision': 'deny',\n"
                    "        'permissionDecisionReason': 'Outside the registered tool policy: ' + basis}}\n")
#: The same value, keys in the same order, with the reason set by item
#: assignment and CHORUS planted in the deny text.
HOOK_OUTPUT_ITEM = ("    if classification == 'prescribed':\n"
                    "        return {}\n"
                    "    output = {'hookEventName': CONTRACT['event'], 'permissionDecision': 'deny'}\n"
                    "    output['permissionDecisionReason'] = 'Outside the CHORUS tool policy: ' + basis\n"
                    "    return {'hookSpecificOutput': output}\n")
AUDIT_ARGV = ("    argv = [str(executable), *CLI_FLAGS,", "    argv: list[str] = [str(executable), *CLI_FLAGS,")
AUDIT_ARGV_END = "        '--system-prompt', Path(job['system_prompt']).read_text()]\n"


def _discovered_with_rewrites(edits: tuple) -> tuple:
    """discover() of this checkout with files rewritten in memory: `edits`
    is ((path, old, new), ...), each `old` once in its file. Returns
    (surfaces, facts, the rewritten texts by path); the mock is gone when it
    returns."""
    texts = {}
    for rel, old, new in edits:
        text = texts.get(rel) or (ROOT / rel).read_text(encoding="utf-8")
        assert text.count(old) == 1, (rel, old)
        texts[rel] = text.replace(old, new)
    rewritten = {(ROOT / rel).resolve(): t for rel, t in texts.items()}
    real_parse = scan._parse

    def parse(p):
        t = rewritten.get(Path(p).resolve())
        return (t, ast.parse(t)) if t is not None else real_parse(p)

    with mock.patch.object(scan, "_parse", side_effect=parse):
        surfaces, facts = scan.discover(ROOT)
    return surfaces, facts, texts


@lru_cache(maxsize=None)
def _discovered_with_the_round_five_rewrites():
    """discover() of this checkout with two rewrites a reviewer made
    (#4142): `hook_output` sets the deny reason by item assignment, and the
    audit continuation binds its argv by an annotated assignment and then
    removes `--safe-mode` from it. Computed once."""
    return _discovered_with_rewrites((
        (NATIVE_CONTROL, HOOK_OUTPUT_DICT, HOOK_OUTPUT_ITEM),
        (AUDIT_NATIVE, AUDIT_ARGV[0], AUDIT_ARGV[1]),
        (AUDIT_NATIVE, AUDIT_ARGV_END, AUDIT_ARGV_END + "    argv.remove('--safe-mode')\n")))


#: The registered launches and the audit preparer the #4156 rewrites edit.
BATCH_NATIVE = "notes/matched_cborg_2026-09-13/audit_controls/batch_native.py"
RUN_NATIVE = "notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py"
RUN_DIRECT = "notes/claudecode_direct/run_direct_canary.py"
AUDIT_PREPARE = "notes/matched_cborg_2026-09-13/audit_controls/prepare.py"
BATCH_ARGV_END = "            '--system-prompt', Path(row['system_prompt']).read_text()]\n"
DIRECT_ARGV = ('    argv_child = [str(executable), *runtime["cli_flags"],',
               '    argv_child = [str(executable), "--print", "--safe-mode",')
DIRECT_ARGV_END = '                  *permission_arguments(command_policy), "--system-prompt", system_prompt]\n'
POLICY_SYSTEM = ('SYSTEM = """You are the native auditor',
                 "POLICY = 'You must use CHORUS data.'\nSYSTEM = POLICY + \"\"\"You are the native auditor")


@lru_cache(maxsize=None)
def _discovered_with_the_round_six_rewrites():
    """discover() of this checkout with the rewrites of #4156, one per file:
    Codex's reproduction of the first finding (the audit continuation's
    argv initializer that ends at native.py:787 concatenated with `[]`, then
    `--safe-mode` removed from it); a concatenation with no removal (the
    batch continuation's); the native canary's launch with its flags inline
    in the argv list it hands over; the direct canary's with its flags
    inline but concatenated; and Codex's reproduction of the second (a
    sentence in a constant the audit preparer's `SYSTEM` is built from).
    Computed once."""
    return _discovered_with_rewrites((
        (AUDIT_NATIVE, AUDIT_ARGV_END, AUDIT_ARGV_END.replace("read_text()]", "read_text()] + []")
         + "    argv.remove('--safe-mode')\n"),
        (BATCH_NATIVE, BATCH_ARGV_END, BATCH_ARGV_END.replace("read_text()]", "read_text()] + []")),
        (RUN_NATIVE, "argv=[executable,*overlay['cli_flags'],", "argv=[executable,'--print','--safe-mode',"),
        (RUN_DIRECT, DIRECT_ARGV[0], DIRECT_ARGV[1]),
        (RUN_DIRECT, DIRECT_ARGV_END, DIRECT_ARGV_END.replace("system_prompt]", "system_prompt] + []")),
        (AUDIT_PREPARE, POLICY_SYSTEM[0], POLICY_SYSTEM[1])))


#: Codex's reproductions of #4166, written into the audit preparer ahead of
#: its `SYSTEM`: a launch whose argv is a parameter the function rebinds
#: only when `enabled`, and two sentences that reach `SYSTEM` only through a
#: method call on a constant made in a top-level assignment (Codex's
#: `setdefault`, and an assigned `append`).
CODEX_GO = ("def go(argv, enabled):\n"
            "    if enabled:\n"
            "        argv = ['claude', '--safe-mode', '--system-prompt', 'text']\n"
            "    subprocess.run(argv)\n")
METHOD_WRITES = ("POLICY = 'You must use CHORUS data.'\n"
                 "PARTS = {}\n"
                 "DEFAULT_POLICY = PARTS.setdefault('default', POLICY)\n"
                 "RULE = 'Always describe the VOICE cohort.'\n"
                 "LINES = []\n"
                 "ADDED = LINES.append(RULE)\n")


@lru_cache(maxsize=None)
def _discovered_with_the_round_seven_rewrites():
    """discover() of this checkout with the rewrites of #4166: each of the
    four registered native launches writes `--print` and `--safe-mode` as
    literal elements of the argv list it hands over, in place of the
    starred flags; Codex's `go(argv, enabled)` is added to the audit
    preparer; and that module's `SYSTEM` is built from two constants that
    a method call in a top-level assignment fills (`METHOD_WRITES`).
    Computed once."""
    flags = "'--print', '--safe-mode',"
    return _discovered_with_rewrites((
        (AUDIT_NATIVE, AUDIT_ARGV[0], AUDIT_ARGV[0].replace("*CLI_FLAGS,", flags)),
        (BATCH_NATIVE, "*native.CLI_FLAGS,", flags),
        (RUN_NATIVE, "argv=[executable,*overlay['cli_flags'],", "argv=[executable,'--print','--safe-mode',"),
        (RUN_DIRECT, DIRECT_ARGV[0], DIRECT_ARGV[1]),
        (AUDIT_PREPARE, POLICY_SYSTEM[0], CODEX_GO + METHOD_WRITES
         + "SYSTEM = ''.join(PARTS.values()) + ''.join(LINES) + \"\"\"You are the native auditor")))


class TestTheSkillFiles(unittest.TestCase):
    def test_the_skill_declares_name_and_description(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front = text.split("---", 2)[1]
        self.assertIn("name: d4d-generation-specificity-audit", front)
        self.assertIn("description:", front)

    def test_the_exceptions_file_parses_and_every_entry_has_a_reason(self):
        entries = scan.load_exceptions(SKILL / "exceptions.yaml")
        self.assertGreater(len(entries), 0)
        for e in entries:
            self.assertTrue(e["reason"].strip(), e)
            self.assertTrue(e["decision"].strip(), e)
        globs = {g for e in entries for g in e["_paths"]}
        for seeded in ("src/data_sheets_schema/profiles.py", "data/preprocessed/source_manifest.yaml",
                       "src/download/prompts/components/*.md",
                       "src/data_sheets_schema/constants/projects.py"):
            self.assertIn(seeded, globs)

    def test_a_malformed_exception_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "x.yaml"
            for text, why in (("exceptions:\n  - path: a.py\n    category: gc_project\n    decision: '#1'\n",
                               "reason"),
                              ("exceptions:\n  - path: a.py\n    reason: r\n    decision: d\n", "token"),
                              ("exceptions:\n  - path: a.py\n    token: 'x('\n    reason: r\n    decision: d\n",
                               "malformed regex"),
                              ("- path: a.py\n", "top level"),
                              ("exceptions:\n  - path: [1]\n    category: gc_project\n    reason: r\n"
                               "    decision: d\n", "path")):
                bad.write_text(text, encoding="utf-8")
                with self.subTest(why=why), self.assertRaisesRegex(scan.ConfigError, why):
                    scan.load_exceptions(bad)

    def test_a_malformed_token_file_is_refused(self):
        spec = (SKILL / "tokens.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "tokens.yaml"
            bad.write_text(spec.replace("    - 'Lundberg'\n", "    - 'Lundberg'\n    - 'unbalanced('\n"),
                           encoding="utf-8")
            with self.assertRaisesRegex(scan.ConfigError, "malformed regex"):
                scan.load_tokens(ROOT, bad)
            bad.write_text("extensions:\n  - gc_project\n", encoding="utf-8")
            with self.assertRaisesRegex(scan.ConfigError, "mappings"):
                scan.load_tokens(ROOT, bad)

    def test_the_tokens_come_from_the_neutrality_test_and_the_skill(self):
        tokens = _tokens()
        sources = {t.source for t in tokens}
        self.assertIn("tests/test_neutral_generation_schema.py:STUDY_IDENTITY", sources)
        self.assertIn("tokens.yaml", sources)
        self.assertEqual({t.category for t in tokens}, set(scan.CATEGORIES))

    def test_the_uva_dataverse_releases_are_gc_tokens(self):
        """CM4AI (B35XWX, F3TD5R, K7TGEM, HIGT4C) and CHORUS (XNBOPG) publish
        under the UVA Dataverse prefix 10.18130 (#4027). Each bare release id
        is a token of its own and the prefix catches an id with none, so no
        text here passes on another token's match (#4057)."""
        tokens = list(_tokens())
        for text, spans in (("the HIGT4C release", {"HIGT4C"}), ("the XNBOPG release", {"XNBOPG"}),
                            ("the K7TGEM release", {"K7TGEM"}), ("the F3TD5R release", {"F3TD5R"}),
                            ("cite doi:10.18130/V3/ABCDEF", {"10.18130/"}),
                            ("Use doi:10.18130/V3/HIGT4C as id", {"10.18130/", "HIGT4C"}),
                            ("see https://doi.org/10.18130/V3/XNBOPG", {"10.18130/", "XNBOPG"})):
            with self.subTest(text=text):
                got = {m for _, _, t, m in scan.match_text(text, tokens) if t.category == "gc_project"}
                self.assertEqual(got, spans)


class TestTheExitStatus(unittest.TestCase):
    """Exit 1 means violations, 0 a clean scan; a scan that did not happen is
    2 (#4027, #4057, #4058)."""

    def _main(self, *argv):
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr"), mock.patch("sys.stdout"):
            return scan.main(["--root", str(ROOT), "--report", str(Path(d) / "r.md"), *argv])

    def test_the_exit_status_contract(self):
        self.assertEqual(scan.exit_status(True, []), 0)
        self.assertEqual(scan.exit_status(True, [{"path": "x"}]), 1)
        self.assertEqual(scan.exit_status(False, [{"path": "x"}]), 2)
        self.assertEqual(scan.exit_status(False, []), 2)

    def test_violations_are_exit_1(self):
        """The completed scan of this checkout has violations (the GC names
        in CLAUDE.md and the launchers), so run() and main() both say 1."""
        result = _full_run()
        self.assertTrue(result["violations"])
        self.assertEqual(result["exit"], 1)
        with mock.patch.object(scan, "run", return_value=result):
            self.assertEqual(self._main(), 1)

    def test_a_failed_self_test_in_a_full_scan_is_exit_2(self):
        ignore = list(scan.IGNORE)          # load_tokens resets the module's ignore list
        try:
            with tempfile.TemporaryDirectory() as d:
                empty = _write(Path(d) / "tokens.yaml", "imported_lists: {}\nextensions: {}\n")
                self.assertEqual(self._main("--tokens", str(empty)), 2)
        finally:
            scan.IGNORE[:] = ignore

    def test_without_pyyaml_the_scan_is_exit_2(self):
        """PyYAML is imported before main() runs: its absence must not exit 1,
        which reads as violations (#4058)."""
        code = ("import runpy, sys\nsys.modules['yaml'] = None\n"
                f"sys.argv = ['scan.py', '--self-test-only']\nrunpy.run_path({str(SKILL / 'scan.py')!r}, "
                "run_name='__main__')\n")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("PyYAML", proc.stderr)

    def test_a_malformed_token_regex_is_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = _write(Path(d) / "tokens.yaml", (SKILL / "tokens.yaml").read_text(encoding="utf-8")
                         .replace("    - 'Lundberg'\n", "    - 'Lundberg'\n    - 'unbalanced('\n"))
            self.assertEqual(self._main("--tokens", str(bad)), 2)
            self.assertEqual(self._main("--tokens", str(bad), "--self-test-only"), 2)

    def test_a_malformed_exception_is_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = _write(Path(d) / "x.yaml", "exceptions:\n  - path: a.py\n    token: 'x('\n    reason: r\n"
                                             "    decision: d\n")
            self.assertEqual(self._main("--exceptions", str(bad)), 2)
            _write(bad, "- path: a.py\n")
            self.assertEqual(self._main("--exceptions", str(bad)), 2)

    def test_a_missing_token_file_is_exit_2_in_self_test_mode(self):
        self.assertEqual(self._main("--tokens", "/nonexistent/tokens.yaml", "--self-test-only"), 2)

    def test_an_unexpected_error_is_exit_2(self):
        with mock.patch.object(scan, "discover", side_effect=RuntimeError("boom")):
            self.assertEqual(self._main(), 2)

    def test_a_derivation_that_finds_nothing_is_exit_2(self):
        with mock.patch.object(scan, "discover", side_effect=scan._not_derived("x", "y")):
            self.assertEqual(self._main(), 2)

    def test_a_surface_that_cannot_be_read_is_exit_2(self):
        """A discovered file the scan cannot read is not vouched for: the scan
        stops rather than report a result without it."""
        surfaces = scan.Surfaces()
        surfaces.add("no/such/surface_4027.md", "api", "model_facing", "live", "test")
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(scan, "discover", return_value=(surfaces, {})), \
                mock.patch("sys.stderr", err), mock.patch("sys.stdout"):
            code = scan.main(["--root", str(ROOT), "--report", str(Path(d) / "r.md")])
        self.assertEqual(code, 2)
        self.assertIn("no/such/surface_4027.md", err.getvalue())
        self.assertIn("could not be read", err.getvalue())


class TestAstCapabilities(unittest.TestCase):
    """The CLI refuses an unavailable scanner capability before any report."""

    def test_missing_capabilities_are_configuration_errors_in_both_cli_modes(self):
        capabilities = ("Match", "MatchAs", "MatchStar", "MatchMapping", "match_case")
        for missing in [(name,) for name in capabilities] + [capabilities]:
            for mode in ([], ["--self-test-only"]):
                with self.subTest(missing=missing, mode=mode), tempfile.TemporaryDirectory() as d:
                    # Simulate an older AST interface without replacing any
                    # of its available parsing or traversal implementations.
                    limited = SimpleNamespace(**{k: v for k, v in vars(ast).items() if k not in missing})
                    report, summary = Path(d) / "report.md", Path(d) / "report.json"
                    err, stdout = io.StringIO(), io.StringIO()
                    with mock.patch.object(scan, "ast", limited), mock.patch("sys.stderr", err), \
                            mock.patch("sys.stdout", stdout):
                        code = scan.main(["--root", str(ROOT), "--report", str(report),
                                          "--json", str(summary), *mode])
                    self.assertEqual(code, 2, err.getvalue())
                    self.assertIn("configuration error", err.getvalue())
                    self.assertIn("AST capabilities", err.getvalue())
                    self.assertIn(sys.executable, err.getvalue())
                    self.assertIn(sys.version.split()[0], err.getvalue())
                    for name in missing:
                        self.assertIn("ast." + name, err.getvalue())
                    self.assertNotIn("Traceback", err.getvalue())
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertFalse(report.exists())
                    self.assertFalse(summary.exists())

    def test_help_remains_available_without_match_capabilities(self):
        limited = SimpleNamespace(**{k: v for k, v in vars(ast).items()
                                     if k not in {"Match", "MatchAs", "MatchStar", "MatchMapping", "match_case"}})
        stdout, err = io.StringIO(), io.StringIO()
        with mock.patch.object(scan, "ast", limited), mock.patch("sys.stdout", stdout), \
                mock.patch("sys.stderr", err), self.assertRaises(SystemExit) as stopped:
            scan.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn("--self-test-only", stdout.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_supported_cli_self_test_still_reports_its_seeded_results(self):
        with tempfile.TemporaryDirectory() as d:
            report, summary = Path(d) / "report.md", Path(d) / "report.json"
            stdout, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", err):
                code = scan.main(["--root", str(ROOT), "--self-test-only", "--report", str(report),
                                  "--json", str(summary)])
            self.assertEqual(code, 0, err.getvalue())
            result = json.loads(stdout.getvalue())
            self.assertTrue(result["passed"])
            self.assertEqual(result["problems"], [])
            self.assertGreater(result["imported_from_neutrality_test"], 0)
            self.assertTrue(all(result["token_counts"].values()))
            self.assertEqual(err.getvalue(), "")
            self.assertFalse(report.exists())
            self.assertFalse(summary.exists())


class TestTheScannerSees(unittest.TestCase):
    def test_the_seeded_self_test_passes(self):
        result = scan.self_test(list(_tokens()))
        self.assertTrue(result["passed"], result["problems"])

    def test_a_scanner_with_no_tokens_fails_its_self_test(self):
        self.assertFalse(scan.self_test([])["passed"])

    def test_the_self_test_fails_when_python_lines_are_wrong(self):
        """The self-test checks the line of every planted Python item (#4026):
        with the token-based line mapping removed, the implicitly
        concatenated literal is reported at its first line and the self-test
        fails."""
        with mock.patch.object(scan, "_string_lines", return_value=None):
            result = scan.self_test(list(_tokens()))
        self.assertFalse(result["passed"])
        self.assertTrue(any("physionet" in p for p in result["problems"]), result["problems"])

    def test_every_python_hit_is_on_a_line_that_holds_it(self):
        """Implicitly concatenated literals (constants/methods.py:58-64,
        PHASE_INSTRUCTIONS in api_runner) are reported on the physical line
        of each part (#4026), so the reported line's text holds the match."""
        tokens = list(_tokens())
        for rel in ("src/data_sheets_schema/constants/methods.py", "src/data_sheets_schema/api_runner.py",
                    "notes/matched_cborg_2026-09-13/prepare_registration.py", "src/data_sheets_schema/grounding.py"):
            lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
            hits = scan.scan_file(ROOT, scan.Surface(rel, ["api"], "run_shaping", "live", "test"), tokens)
            self.assertTrue(hits, rel)
            for h in hits:
                with self.subTest(rel=rel, line=h["line"], match=h["match"]):
                    self.assertIn(h["match"].lower(), lines[h["line"] - 1].lower())
        methods = scan.scan_file(ROOT, scan.Surface("src/data_sheets_schema/constants/methods.py", ["api"],
                                                    "run_shaping", "live", "test"), tokens)
        self.assertEqual({h["line"] for h in methods if h["match"] == "AI-READI"
                          and h["context"] == "string_literal"}, {60, 63})

    @unittest.skipIf(sys.version_info < (3, 12), "an f-string's parts are tokens from Python 3.12")
    def test_a_concatenated_f_string_part_is_reported_on_its_own_line(self):
        """The parts of an f-string concatenated across lines fold into one
        constant; its line is read from the f-string's own tokens, not the
        first line (#4130)."""
        code = "x = (f'{basis}, respelled: {problem}. This refusal '\n     f'the attempt; run CHORUS exactly: {s}')\n"
        self.assertEqual([(u[0], u[1]) for u in scan._python_units(code) if "CHORUS" in u[2]], [(2, "string_literal")])

    def test_a_non_ascii_prefix_does_not_shift_a_literal(self):
        """`ast` columns are UTF-8 bytes and `tokenize` columns are
        characters: a literal after a non-ASCII one on the same line must
        still be read from its own tokens."""
        units = list(scan._python_units("x = ('é' 'ü'); y = ('see '\n     'CHORUS here')\n"))
        self.assertIn((2, "string_literal", "CHORUS here"), [(u[0], u[1], u[2]) for u in units])

    def _planted(self, rel: str, line: str, after: str | None = None):
        """`_plant`: a line planted in a copy of a real surface, scanned
        under the role discover() gives it (inside a constant or a function
        whose span discovery derived, with `after`)."""
        return _plant(rel, line, after)

    def test_a_gc_token_planted_in_a_playbook_is_a_violation(self):
        for rel in (".claude/commands/d4d-full-core.md", ".claude/commands/d4d-input-deep-research.md"):
            with self.subTest(rel=rel):
                planted, _ = self._planted(rel, "Prefer the CM4AI release notes when two sources disagree.")
                self.assertTrue(planted)
                self.assertEqual({h["category"] for h in planted}, {"gc_project"})
                self.assertTrue(all(h["violation"] for h in planted))

    def test_a_gc_token_planted_in_an_agent_a_playbook_names_by_bare_name_is_a_violation(self):
        """d4d-agent.md and d4d-assistant.md name `d4d-validator` by bare name
        only (#4023): the agent is model-facing, not exposed."""
        planted, _ = self._planted(".claude/agents/d4d-validator.md", "Always cite the fairhub page.")
        self.assertTrue(planted)
        self.assertTrue(all(h["violation"] for h in planted))

    def test_a_gc_token_planted_in_claude_md_is_an_interactive_session_violation(self):
        """Claude Code loads CLAUDE.md into the interactive sessions the
        /d4d-* playbooks run in (#4054): a project sentence there is a
        violation of that approach, and, while no registered native launch
        is shown to switch it off, of run_controllers (#4156); of no
        other."""
        surface = _discovered()[0].files["CLAUDE.md"]
        self.assertEqual(surface.roles, dict.fromkeys(SESSION_GATES, "model_facing"))
        planted, _ = self._planted("CLAUDE.md", "Always describe the dataset as AI-READI from FAIRhub.")
        self.assertTrue(planted)
        self.assertTrue(all(h["violation"] and h["gates_in"] == SESSION_GATES for h in planted))

    def test_a_project_branch_planted_in_runner_code_is_a_violation(self):
        planted, _ = self._planted("src/data_sheets_schema/healthsheet.py",
                                   "if __name__ == 'VOICE_PEDIATRIC':\n    pass")
        branch = [h for h in planted if h["match"] == "VOICE_PEDIATRIC" and h["context"] == "code_branch"]
        self.assertTrue(branch)
        self.assertTrue(all(h["violation"] for h in branch))

    def test_a_comment_is_reported_but_does_not_fail(self):
        planted, _ = self._planted("src/data_sheets_schema/healthsheet.py", "# measured on CHORUS rep1")
        comment = [h for h in planted if h["context"] == "comment" and h["match"] == "CHORUS"]
        self.assertTrue(comment)
        self.assertFalse(any(h["violation"] for h in comment))

    def test_a_controller_function_that_renders_model_text_is_model_facing(self):
        """finalization_controls/contract.py:render_instruction writes the
        Phase 4 instruction a native model receives (#4023): a project
        sentence there is a violation; the same sentence in a function that
        renders nothing for a model is not."""
        rel = "notes/matched_cborg_2026-09-13/finalization_controls/contract.py"
        self.assertIn("run_controllers", _discovered()[0].files[rel].approaches)
        planted, _ = self._planted(rel, "def render_instruction_4026():\n    return 'Use the CHORUS release notes.'\n"
                                        "def summarize_4026():\n    return 'Use the CHORUS release notes.'")
        by_function = {h.get("model_text_function"): h["violation"] for h in planted if h["match"] == "CHORUS"}
        self.assertEqual(by_function, {"render_instruction_4026": True, None: False})

    def test_controller_text_a_model_receives_by_data_flow_is_model_facing(self):
        """The system prompt of every registered native run is built from
        module constants a model-text function returns (SYSTEM) and from
        functions whose results are passed to --system-prompt
        (command_guidance, which embeds lookup_guidance): a project sentence
        planted in any of them is a violation, although none is named like a
        renderer (#4054)."""
        sentence = "Prefer the CHORUS release notes when sources disagree."
        for rel, after, line in (
                ("notes/matched_cborg_2026-09-13/audit_controls/prepare.py", 'SYSTEM = """', sentence),
                ("notes/matched_cborg_2026-09-13/finalization_controls/prepare.py", "SYSTEM='''", sentence),
                ("notes/matched_cborg_2026-09-13/native_controls/native_command_policy.py",
                 "'\\n\\n## Registered inline Python commands\\n\\n'", f"        '{sentence} '"),
                ("notes/matched_cborg_2026-09-13/native_controls/native_readonly.py",
                 "'\\n\\n## Registered read-only shell lookups\\n\\n'", f"        '{sentence} '")):
            with self.subTest(rel=rel):
                planted, _ = self._planted(rel, line, after=after)
                chorus = [h for h in planted if h["match"] == "CHORUS"]
                self.assertTrue(chorus)
                self.assertTrue(all(h["violation"] and h.get("model_text_function") for h in chorus), chorus)

    def test_a_main_block_counts_only_where_the_module_runs_as_a_script(self):
        """A `__main__` block runs only when its file runs as a script: an
        approach that only imports the module never executes it (#4054)."""
        text = "def f():\n    return 1\nif __name__ == '__main__':\n    primary = ['CHORUS', 'diabetes']\n"
        imported = scan.Surface("m_4054.py", ["deterministic"], "run_shaping", "live", "test", runs=set())
        run = scan.Surface("m_4054.py", ["deterministic"], "run_shaping", "live", "test")
        quiet = [h for h in _scan_text("m_4054.py", text, imported) if h["match"] == "CHORUS"]
        loud = [h for h in _scan_text("m_4054.py", text, run) if h["match"] == "CHORUS"]
        self.assertTrue(quiet and loud)
        self.assertFalse(any(h["violation"] for h in quiet))
        self.assertTrue(all(h["main_block"] for h in quiet))
        self.assertTrue(all(h["violation"] for h in loud))

    def test_an_exposed_file_never_gates(self):
        """A file a native run is handed but no live text names is exposed:
        not even its code tables gate (#4054)."""
        text = "PROJECTS = ['CHORUS']\nif x == 'CM4AI':\n    pass\n"
        exposed = scan.Surface("s_4054.py", ["native_agentic"], "exposed", "live", "test")
        shaping = scan.Surface("s_4054.py", ["native_agentic"], "run_shaping", "live", "test")
        self.assertFalse(any(h["violation"] for h in _scan_text("s_4054.py", text, exposed)))
        self.assertEqual(sum(h["violation"] for h in _scan_text("s_4054.py", text, shaping)), 2)

    def test_each_approach_judges_a_hit_by_its_own_role(self):
        """One file, exposed to native runs but imported by a deterministic
        arm: the arm's role decides whether a code table gates."""
        surface = scan.Surface("t_4054.py", ["native_agentic", "deterministic"], "run_shaping", "live", "test",
                               roles={"native_agentic": "exposed", "deterministic": "run_shaping"})
        hits = _scan_text("t_4054.py", "PROJECTS = ['CHORUS']\n", surface)
        self.assertEqual([h["gates_in"] for h in hits], [["deterministic"]])

    def test_text_above_the_prompt_body_is_header_not_model_facing(self):
        units = list(scan._markdown_units("# v9\nCHORUS rep2 changelog\n## Prompt body\nRead it.\n",
                                          prompt_header=True))
        self.assertEqual([u[1] for u in units][:3], ["header", "header", "header"])
        self.assertNotIn("header", [u[1] for u in units][3:])

    def test_a_slot_named_examples_is_not_an_example(self):
        """LinkML's `examples` metaslot holds examples; a slot *named*
        `examples` (ExistingUse.examples) is a slot, and its from_schema is
        the namespace value exception #7 covers (#4056)."""
        schema = ("classes:\n  ExistingUse:\n    attributes:\n      examples:\n        name: examples\n"
                  "        from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses\n"
                  "      title:\n        from_schema: https://w3id.org/bridge2ai/data-sheets-schema/uses\n"
                  "slots:\n  foo:\n    examples:\n      - value: an example\n")
        got = {(line, ctx) for line, ctx, _, _ in scan._yaml_units(schema)}
        self.assertIn((6, "value"), got)
        self.assertIn((8, "value"), got)
        self.assertIn((12, "example"), got)
        for rel in ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
                    "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(rel=rel):
                self.assertFalse([line for line, ctx, unit, _ in scan._yaml_units(text)
                                  if ctx == "example" and unit.strip().startswith("from_schema:")])

    def test_the_tests_of_this_audit_are_not_test_dependencies(self):
        """This file plants GC tokens to check the scanner: listing it among
        the tests that pin project-dependent generation would be a false
        positive (#4056); a test that does pin one is still listed."""
        entries, own = scan.scan_tests(ROOT, list(_tokens()))
        me = "tests/test_generation_specificity_skill.py"
        self.assertIn(me, own)
        self.assertNotIn(me, {e["path"] for e in entries})
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d) / "tests/test_x_4056.py", "from data_sheets_schema.api_runner import build_phase\n"
                                                     "def test_it():\n    assert 'CHORUS' in build_phase()\n")
            entries, own = scan.scan_tests(Path(d), list(_tokens()))
        self.assertEqual([(e["path"], e["match"]) for e in entries], [("tests/test_x_4056.py", "CHORUS")])
        self.assertEqual(own, [])


class TestProjectKeyedCode(unittest.TestCase):
    """A project-keyed table, default or key in run-shaping code gates
    (#4024); a sentence that names a project there does not."""

    PLANTED = ('SPECIAL_4024 = frozenset({"CHORUS", "VOICE"})\n'
               'OTHER_4024 = set(["CM4AI"])\n'
               'def planted_4024(d, p, run):\n'
               '    projects = ["AI_READI"]\n'
               '    for q in ("VOICE_PEDIATRIC",):\n'
               '        pass\n'
               '    run(project="CHORUS", choices=["CM4AI"])\n'
               '    x = d["AI_READI"]\n'
               '    return d.get(p, "AI_READI")\n')

    def test_project_keyed_code_in_a_run_shaping_file_is_a_violation(self):
        rel = "src/data_sheets_schema/cli/api.py"
        surface = _discovered()[0].files[rel]
        self.assertEqual(surface.role, "run_shaping")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            text = (ROOT / rel).read_text(encoding="utf-8")
            if not text.endswith("\n"):
                text += "\n"
            _write(root / rel, text + "\n" + self.PLANTED)
            first = len(text.splitlines()) + 2
            hits = [h for h in scan.scan_file(root, surface, list(_tokens())) if h["line"] >= first]
        for h in hits:
            h["exception"] = None
        got = {(h["line"] - first + 1, h["match"]) for h in hits}
        self.assertEqual(got, {(1, "CHORUS"), (1, "VOICE"), (2, "CM4AI"), (4, "AI_READI"),
                               (5, "VOICE_PEDIATRIC"), (7, "CHORUS"), (7, "CM4AI"), (8, "AI_READI"),
                               (9, "AI_READI")})
        for h in hits:
            with self.subTest(line=h["line"], match=h["match"]):
                self.assertEqual(h["context"], "code_table")
                self.assertTrue(scan.is_violation(h))

    def test_a_sentence_naming_a_project_stays_a_string_literal(self):
        units = list(scan._python_units('HELP = "see the CHORUS release notes"\nf(help="the VOICE study")\n'))
        self.assertEqual({u[1] for u in units if "CHORUS" in u[2] or "VOICE" in u[2]}, {"string_literal"})

    #: The forms review round 4 found read as string literals, so a project
    #: default in them never gated in run-shaping code (#4130): an `or`
    #: default (assigned and returned), a value wrapped in a call, an
    #: operator or an f-string, `click.Choice`, a positional argument, regex
    #: and glob tests, argv `.append`/`.extend`, a yielded value. The last
    #: two lines are sentences, which stay text.
    PLANTED_4130 = ('@click.option("--plant-4130", type=click.Choice(["CHORUS", "VOICE"]))\n'     # 1
                    'def planted_4130(plant_project, p, argv):\n'                                  # 2
                    '    project = plant_project or "CM4AI"\n'                                     # 3
                    '    raw = Path("data/raw") / "AI_READI"\n'                                    # 4
                    '    single = Path("data/raw/CHORUS")\n'                                       # 5
                    '    peds = f"data/raw/{p}/VOICE_PEDIATRIC"\n'                                 # 6
                    '    _plant_launch_4130("CHORUS")\n'                                           # 7
                    '    if re.fullmatch("VOICE", p):\n'                                           # 8
                    '        pass\n'                                                               # 9
                    '    if fnmatch.fnmatch(p, "CM4AI*"):\n'                                       # 10
                    '        pass\n'                                                               # 11
                    '    argv.append("AI_READI")\n'                                                # 12
                    '    argv.extend(["CHORUS", "VOICE"])\n'                                       # 13
                    '    joined = "data/" + "CM4AI"\n'                                             # 14
                    '    env = os.environ.get("X") or "VOICE"\n'                                   # 15
                    '    return project or "CHORUS"\n'                                             # 16
                    'def generate_4130():\n'                                                       # 17
                    '    yield "CM4AI"\n'                                                          # 18
                    'TEXT_4130 = plant or "see the VOICE notes"\n'                                 # 19
                    'print(f"Processing {plant} for CHORUS")\n')                                   # 20

    def test_or_defaults_wrapped_values_arguments_and_tests_gate(self):
        rel = "src/data_sheets_schema/cli/api.py"
        surface = _discovered()[0].files[rel]
        text = (ROOT / rel).read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        first = len(text.splitlines()) + 2
        hits = [h for h in _scan_text(rel, text + "\n" + self.PLANTED_4130, surface) if h["line"] >= first]
        got = {(h["line"] - first + 1, h["match"]): (h["context"], h["violation"]) for h in hits}
        table, branch = ("code_table", True), ("code_branch", True)
        self.assertEqual(got, {(1, "CHORUS"): table, (1, "VOICE"): table, (3, "CM4AI"): table,
                               (4, "AI_READI"): table, (5, "CHORUS"): table, (6, "VOICE_PEDIATRIC"): table,
                               (7, "CHORUS"): table, (8, "VOICE"): branch, (10, "CM4AI"): branch,
                               (12, "AI_READI"): table, (13, "CHORUS"): table, (13, "VOICE"): table,
                               (14, "CM4AI"): table, (15, "VOICE"): table, (16, "CHORUS"): table,
                               (18, "CM4AI"): table, (19, "VOICE"): ("string_literal", False),
                               (20, "CHORUS"): ("string_literal", False)})

    def test_an_or_default_is_a_table_like_a_conditional_one(self):
        """`x if x else "A"` was a table and `x or "A"` a string literal; a
        lookup default and the same default after `or` differed too (#4130)."""
        for code in ('x = project if project else "CHORUS"\n', 'x = project or "CHORUS"\n',
                     'x = os.environ.get("X", "CHORUS")\n', 'x = os.environ.get("X") or "CHORUS"\n',
                     'def f(project):\n    return project or "CHORUS"\n'):
            with self.subTest(code=code):
                self.assertEqual({u[1] for u in scan._python_units(code) if "CHORUS" in u[2]}, {"code_table"})

    def test_the_failed_extraction_table_gates_whole(self):
        """scripts/fix_failed_extractions.py keys each failed file on a
        project: its 'column' entries gated, and its `Path(...)` values, which
        name the same projects and platforms, gate too (#4130)."""
        rel = "scripts/fix_failed_extractions.py"
        surface = _discovered()[0].files[rel]
        self.assertEqual(surface.roles, {"legacy_monolithic": "run_shaping"})
        text = (ROOT / rel).read_text(encoding="utf-8")
        wrapped = {i for i, x in enumerate(text.splitlines(), 1) if re.search(r"Path\('\.\./.*(AI_READI|VOICE)", x)}
        self.assertEqual(len(wrapped), 4)
        hits = [h for h in _scan_text(rel, text, surface) if h["line"] in wrapped and h["category"] == "gc_project"]
        self.assertEqual(len(hits), 10)
        self.assertTrue(all(h["context"] == "code_table" and h["violation"] and h["gates_in"] == ["legacy_monolithic"]
                            for h in hits), hits)


# Native scanner support can ship before the native runtime. Only this complete
# optional group may be absent from a standalone API checkout (#4514).
_OPTIONAL_NATIVE_MODEL_FACING = scan.NATIVE_SHARED_MODULES


def _missing_model_facing_modules(root, closures):
    def paths(name):
        return (f"src/data_sheets_schema/{name}.py",
                f"src/data_sheets_schema/{name}/__init__.py")
    # The roster lists only modules main carries; the native group left it with
    # 88f909562 because its sources are on the native branch. It stays a
    # candidate here, so a native source that lands is required (#5076).
    required = scan.MODEL_FACING_MODULES | _OPTIONAL_NATIVE_MODEL_FACING
    # Any present native source makes the whole group mandatory: a partial
    # implementation or missing closure edge must not become an exemption.
    if not any((root / path).exists() or (root / path).is_symlink()
               for name in _OPTIONAL_NATIVE_MODEL_FACING for path in paths(name)):
        required = required - _OPTIONAL_NATIVE_MODEL_FACING
    return {name for name in required if not any(path in closures for path in paths(name))}


class TestNativeSharedModulesGateWithoutTheDerivation(unittest.TestCase):
    """#5082: the native group left MODEL_FACING_MODULES (88f909562) but keeps the
    list's guarantee: a native module the derivation misses still gates."""

    def test_a_native_module_the_derivation_misses_is_model_facing_and_gates(self):
        line = 'NOTE_5082 = "Describe the CHORUS cohort."'
        for name in sorted(scan.NATIVE_SHARED_MODULES):
            rel = f"src/data_sheets_schema/{name}.py"
            role = scan._module_role(ROOT / rel, frozenset())
            self.assertEqual(role, "model_facing", name)
            hits = _scan_text(rel, line + "\n", scan.Surface(rel, ["native_agentic"], role, "live", "t"))
            self.assertTrue(hits and all(h["violation"] for h in hits), (name, hits))

    def test_the_group_is_not_listed_so_main_s_list_cross_check_holds(self):
        self.assertFalse(scan.NATIVE_SHARED_MODULES & scan.MODEL_FACING_MODULES)


class TestModelFacingClosureCoverage(unittest.TestCase):
    def test_all_optional_native_sources_absent(self):
        with tempfile.TemporaryDirectory() as d:
            ordinary = scan.MODEL_FACING_MODULES - _OPTIONAL_NATIVE_MODEL_FACING
            closure = {f"src/data_sheets_schema/{name}.py" for name in ordinary}
            self.assertEqual(_missing_model_facing_modules(Path(d), closure), set())

    def test_an_ordinary_missing_module_is_never_exempted(self):
        with tempfile.TemporaryDirectory() as d:
            ordinary = scan.MODEL_FACING_MODULES - _OPTIONAL_NATIVE_MODEL_FACING
            closure = {f"src/data_sheets_schema/{name}.py" for name in ordinary if name != "api_runner"}
            # Its file is absent too: filtering the whole roster by existence
            # would silently hide this mandatory missing module.
            self.assertEqual(_missing_model_facing_modules(Path(d), closure), {"api_runner"})

    def test_present_native_sources_require_every_closure_edge(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in _OPTIONAL_NATIVE_MODEL_FACING:
                _write(root / f"src/data_sheets_schema/{name}.py", "VALUE = 1\n")
            closure = {f"src/data_sheets_schema/{name}.py"
                       for name in scan.MODEL_FACING_MODULES | _OPTIONAL_NATIVE_MODEL_FACING}
            self.assertEqual(_missing_model_facing_modules(root, closure), set())
            closure.remove("src/data_sheets_schema/native_shared_stage.py")
            self.assertEqual(_missing_model_facing_modules(root, closure), {"native_shared_stage"})

    def test_a_dangling_native_module_entry_is_not_absence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            link = root / "src/data_sheets_schema/native_shared_render.py"
            link.parent.mkdir(parents=True)
            link.symlink_to("missing.py")
            ordinary = scan.MODEL_FACING_MODULES - _OPTIONAL_NATIVE_MODEL_FACING
            closure = {f"src/data_sheets_schema/{name}.py" for name in ordinary}
            self.assertEqual(_missing_model_facing_modules(root, closure), _OPTIONAL_NATIVE_MODEL_FACING)

    def test_partial_native_source_group_is_not_an_exemption(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / "src/data_sheets_schema/native_shared_render.py", "VALUE = 1\n")
            ordinary = scan.MODEL_FACING_MODULES - _OPTIONAL_NATIVE_MODEL_FACING
            closure = {f"src/data_sheets_schema/{name}.py" for name in ordinary | {"native_shared_render"}}
            self.assertEqual(_missing_model_facing_modules(root, closure),
                             _OPTIONAL_NATIVE_MODEL_FACING - {"native_shared_render"})


class TestDiscovery(unittest.TestCase):
    """Surfaces are derived from the code, not a glob list (#4023, #4054)."""

    @classmethod
    def setUpClass(cls):
        cls.surfaces, cls.facts = _discovered()

    @staticmethod
    def _code_tokens(path: Path) -> str:
        """The module's names and operators, space-separated, with comments and
        strings dropped: a mechanism independent of the scanner's ast reading,
        and blind to a docstring that only mentions a client."""
        out = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
                if tok.type in (tokenize.NAME, tokenize.OP):
                    out.append(tok.string)
                elif tok.type in (tokenize.NEWLINE, tokenize.NL):
                    out.append("\n")
        except (tokenize.TokenError, SyntaxError, UnicodeDecodeError):
            return ""
        return " ".join(out)

    def test_every_module_that_calls_a_model_client_is_a_surface(self):
        """Over every tree discovery must read, src/, notes/ and scripts/
        (#4054): scripts/fix_failed_extractions.py calls pydantic_ai."""
        client = re.compile(r"\b(?:import (?:anthropic|openai|pydantic_ai|aurelian)\b|from (?:anthropic|openai|"
                            r"pydantic_ai|aurelian)\b)|\. messages \. (?:create|stream) \(|\. ChatCompletion \. create \(")
        found = []
        for top in DISCOVERY_TREES:
            for p in sorted((ROOT / top).rglob("*.py")):
                rel = p.relative_to(ROOT).as_posix()
                if scan._is_test(rel) or scan.REGISTERED_COPY.search(rel):
                    continue
                if client.search(self._code_tokens(p)):
                    found.append(rel)
        self.assertIn("src/schema_extract/process_d4d_claude_API_temp0.py", found)
        self.assertIn("scripts/fix_failed_extractions.py", found)
        self.assertEqual([r for r in found if r not in self.surfaces.files], [])
        self.assertEqual(set(self.facts["python_roots"]), set(DISCOVERY_TREES))

    def test_the_schema_extract_generator_is_a_monolithic_legacy_surface(self):
        rel = "src/schema_extract/process_d4d_claude_API_temp0.py"
        self.assertIn("legacy_monolithic", self.surfaces.files[rel].approaches)
        meaning = _meaning()
        self.assertEqual(meaning["legacy"][rel]["shape"], "MONOLITHIC")

    def test_the_monolithic_verdict_lists_every_monolithic_script(self):
        meaning = _meaning()
        mono = sorted(p for p, v in meaning["legacy"].items() if v["shape"] == "MONOLITHIC")
        self.assertGreaterEqual(set(mono), {"src/download/process_concatenated_d4d.py",
                                            "src/download/process_concatenated_d4d_claude.py",
                                            "src/schema_extract/process_d4d_claude_API_temp0.py"})
        line = next(v for v in meaning["verdict"] if v.startswith("The monolithic shape"))
        for p in mono:
            self.assertIn(p, line)

    def test_the_live_controllers_are_discovered(self):
        for rel in ("notes/matched_cborg_2026-09-13/finalization_controls/contract.py",
                    "notes/matched_cborg_2026-09-13/finalization_controls/native.py",
                    "notes/matched_cborg_2026-09-13/finalization_controls/prepare.py",
                    "notes/matched_cborg_2026-09-13/finalization_controls/registration.py",
                    "notes/matched_cborg_2026-09-13/run_api_canary.py",
                    "notes/matched_cborg_2026-09-13/native_context_control.py",
                    "notes/matched_cborg_2026-09-13/prepare_registration.py",
                    "notes/claudecode_direct/prepare_direct.py",
                    "notes/claudecode_direct/bind_direct_launch.py"):
            with self.subTest(rel=rel):
                self.assertIn("run_controllers", self.surfaces.files[rel].approaches)
        for rel in ("notes/matched_cborg_2026-09-13/native_controls/system.md", "notes/claudecode_direct/system.md"):
            self.assertEqual(self.surfaces.files[rel].role, "model_facing")

    def test_evaluation_and_probes_are_listed_but_never_gate(self):
        for rel in ("notes/matched_cborg_2026-09-13/evaluation_controls/run_evaluation.py",
                    "notes/matched_cborg_2026-09-13/evaluation_controls/closure.py",
                    "notes/matched_cborg_2026-09-13/native_controls/transport_probe.py"):
            with self.subTest(rel=rel):
                self.assertEqual(self.surfaces.files[rel].approaches, ["other_model_client"])
        self.assertFalse(scan.APPROACHES["other_model_client"][0])

    def test_a_new_controller_directory_needs_no_glob_edit(self):
        """A seed that builds a generation request, a helper it imports, a
        launcher that imports it and a file it pins are controllers; a probe
        and an evaluation module are not."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes" / "exp_2099" / "brand_new_controls"
            _write(base / "launch.py", "from data_sheets_schema.api_runner import RunSpec\nimport helper\n"
                                       "PINNED = ['pinned_tool.py']\nspec = RunSpec\n")
            _write(base / "helper.py", "X = 1\n")
            _write(base / "pinned_tool.py", "Y = 1\n")
            _write(base / "run_it.py", "import launch\n")
            _write(base / "probe_it.py", "from data_sheets_schema.api_runner import RunSpec\n")
            _write(root / "notes" / "exp_2099" / "evaluation_controls" / "score.py",
                   "import sys\nfrom data_sheets_schema.api_runner import build_phase\n")
            parsed = {p.resolve(): scan._parse(p) for p in (root / "notes").rglob("*.py")}
            controllers, why, _ = scan.run_controllers(root, parsed, scan._notes_index(root, parsed))
        self.assertEqual(set(controllers), {f"notes/exp_2099/brand_new_controls/{n}" for n in
                                            ("launch.py", "helper.py", "pinned_tool.py", "run_it.py")})
        self.assertIn("builds a generation request", why["notes/exp_2099/brand_new_controls/launch.py"])
        self.assertIn("runs a controller", why["notes/exp_2099/brand_new_controls/run_it.py"])

    def test_a_launcher_under_scripts_or_src_is_a_controller(self):
        """A launcher outside notes/ that builds a RunSpec for a project
        table and calls the runner's execute is a run controller whose
        table gates; a src module that only uses a builder, and a module in
        a generation closure, are not launchers (#4054)."""
        launcher = ("from data_sheets_schema.api_runner import RunSpec, execute\n"
                    "PROJECTS = ['CHORUS', 'AI_READI']\n"
                    "def main():\n    for project in PROJECTS:\n"
                    "        if project == 'CHORUS':\n            pass\n"
                    "        execute(RunSpec(project=project))\n")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            _write(root / scan.RUNNER, "def execute(spec):\n    pass\nclass RunSpec:\n    pass\n")
            _write(root / "scripts/launch_new_arm_4054.py", launcher)
            _write(root / "src/data_sheets_schema/launch_new_arm_4054.py",
                   launcher.replace("from data_sheets_schema.api_runner import RunSpec, execute",
                                    "from data_sheets_schema import api_runner\nRunSpec = api_runner.RunSpec")
                   .replace("execute(RunSpec", "api_runner.execute(RunSpec"))
            _write(root / "src/data_sheets_schema/review_only_4054.py",
                   "from data_sheets_schema.api_runner import RunSpec\nPROJECTS = ['CHORUS']\n")
            _write(root / "src/data_sheets_schema/in_closure_4054.py", launcher)
            parsed = _parsed(root, "src", "notes", "scripts")
            controllers, why, _ = scan.run_controllers(
                root, parsed, scan._notes_index(root, parsed),
                exclude=frozenset({"src/data_sheets_schema/in_closure_4054.py"}))
            self.assertEqual(set(controllers), {"scripts/launch_new_arm_4054.py",
                                                "src/data_sheets_schema/launch_new_arm_4054.py"})
            self.assertIn("launches a generation run (execute()", why["scripts/launch_new_arm_4054.py"])
            surface = scan.Surface("scripts/launch_new_arm_4054.py", ["run_controllers"], "run_shaping", "live", "t")
            hits = scan.scan_file(root, surface, list(_tokens()))
        for h in hits:
            h["exception"] = None
        self.assertEqual({(h["match"], h["context"]) for h in hits if scan.is_violation(h)},
                         {("CHORUS", "code_table"), ("AI_READI", "code_table"), ("CHORUS", "code_branch")})

    def test_bare_names_and_slash_commands_name_a_playbook_or_agent(self):
        names = {"d4d-validator": ".claude/agents/d4d-validator.md",
                 "d4d-rubric10": ".claude/agents/d4d-rubric10.md",
                 "d4d-full-core": ".claude/commands/d4d-full-core.md"}
        self.assertEqual(scan._named_claude_files("see the `d4d-validator` agent", names),
                         {".claude/agents/d4d-validator.md"})
        self.assertEqual(scan._named_claude_files("run /d4d-full-core first", names),
                         {".claude/commands/d4d-full-core.md"})
        self.assertEqual(scan._named_claude_files("the d4d-rubric10-semantic agent", names), set())
        self.assertEqual(scan._named_claude_files("read .claude/agents/d4d-validator.md", names),
                         {".claude/agents/d4d-validator.md"})
        self.assertIn(".claude/agents/d4d-validator.md", self.facts["native_referenced"])
        self.assertEqual(self.surfaces.files[".claude/agents/d4d-validator.md"].role, "model_facing")

    def test_a_text_names_files_by_path_module_and_memory(self):
        """Every file a playbook, agent, assistant instruction or controller
        names is followed, not only playbooks and agents (#4054); a file the
        text runs is marked so; a templated path names no file."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ("src/github/gen_4054.py", "scripts/tool_4054.py", "notes/guide_4054.md", "CLAUDE.md",
                        "src/data_sheets_schema/__init__.py", "src/data_sheets_schema/pair_4054.py",
                        "src/download/prompts/components/X.md", "tests/test_y_4054.py"):
                _write(root / rel, "x\n")
            text = ("Run:\n    python3 src/github/gen_4054.py --out x\nSee `notes/guide_4054.md` and "
                    "scripts/tool_4054.py (see CLAUDE.md).\npoetry run python -m data_sheets_schema.pair_4054 a\n"
                    "Read src/download/prompts/components/{PROJECT}.md and tests/test_y_4054.py.\n")
            got = scan._named_files(root, text, {})
        self.assertEqual(got, {"src/github/gen_4054.py": True, "notes/guide_4054.md": False,
                               "scripts/tool_4054.py": False, "CLAUDE.md": False,
                               "src/data_sheets_schema/pair_4054.py": True})

    def test_files_the_assistant_tells_the_model_to_run_are_surfaces(self):
        """d4d_assistant_create.md runs src/github/generate_d4d_metadata.py
        and validate_d4d_completeness.py (#4054). The instructions are
        loaded by /d4d-assistant and /d4d-webfetch, so the scripts are
        native_agentic surfaces; the @d4dassistant workflow loads no
        instruction file, so they are not the GitHub assistant's (#4093)."""
        for rel in ("src/github/generate_d4d_metadata.py", "src/github/validate_d4d_completeness.py"):
            with self.subTest(rel=rel):
                surface = self.surfaces.files[rel]
                self.assertEqual(surface.roles, {"native_agentic": "run_shaping"})
                self.assertEqual(surface.runs, {"native_agentic"})
                self.assertIn(".github/workflows/d4d_assistant_create.md", self.facts["named_files"][rel]["by"])

    def test_no_registered_launch_is_shown_to_switch_the_session_off(self):
        """CLAUDE.md is the project memory an interactive session loads; the
        assistant instructions name it but do not hand it over (#4054). Each
        of the four registered native launches passes its flags through a
        starred module constant or record field (`*CLI_FLAGS`,
        `*native.CLI_FLAGS`, `*overlay['cli_flags']`,
        `*runtime['cli_flags']`), which the sound rule does not follow, so
        none is shown to pass `--safe-mode` or `--bare`, and the session's
        surfaces are run_controllers surfaces too (#4156)."""
        it = self.facts["interactive"]
        self.assertIn("CLAUDE.md", it["memory"])
        self.assertIn(".github/workflows/d4d_assistant_create.md", it["memory_named_by"])
        self.assertNotIn("CLAUDE.md", self.facts["named_files"])
        spread = {"notes/claudecode_direct/run_direct_canary.py": "`*runtime['cli_flags']`",
                  "notes/matched_cborg_2026-09-13/audit_controls/batch_native.py": "`*native.CLI_FLAGS`",
                  "notes/matched_cborg_2026-09-13/audit_controls/native.py": "`*CLI_FLAGS`",
                  "notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py": "`*overlay['cli_flags']`"}
        self.assertEqual({x["site"].split(":")[0] for x in it["launches"]}, set(spread))
        for x in it["launches"]:
            with self.subTest(site=x["site"]):
                self.assertIsNone(x["carries"])
                self.assertIsNone(x["memory_off"])
                # its argv list is shown to be what it hands over: only the
                # starred elements stop the proof
                self.assertEqual(len(x["evidence"]), 1, x["evidence"])
                self.assertIn(spread[x["site"].split(":")[0]], x["evidence"][0])
                self.assertIn("are not followed", x["evidence"][0])
        self.assertEqual(it["launches_without_customizations_off"], sorted(x["site"] for x in it["launches"]))
        self.assertEqual(it["launches_without_memory_off"], sorted(x["site"] for x in it["launches"]))
        self.assertEqual(it["customizations_off"], [])
        self.assertEqual(self.surfaces.files["CLAUDE.md"].roles, dict.fromkeys(SESSION_GATES, "model_facing"))

    def test_the_project_settings_and_the_hooks_they_run_are_session_surfaces(self):
        """The settings files and the scripts their hooks run, read here with
        json, independently of the scanner, are interactive_session
        surfaces; a project default in a hook script or in the settings' env
        block gates there (#4131, #4130), and in run_controllers while no
        registered launch is shown to switch them off (#4156)."""
        settings = [rel for rel in (".claude/settings.json", ".claude/settings.local.json") if (ROOT / rel).is_file()]
        self.assertIn(".claude/settings.json", settings)
        commands = []

        def walk(x):
            if isinstance(x, dict):
                commands.extend(v for k, v in x.items() if k == "command" and isinstance(v, str))
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        for rel in settings:
            walk(json.loads((ROOT / rel).read_text(encoding="utf-8")).get("hooks"))
        hooks = sorted({m.group(0) for c in commands for m in re.finditer(r"\.claude/hooks/[\w.-]+\.py", c)})
        self.assertTrue(hooks)
        it = self.facts["interactive"]
        self.assertEqual(it["settings"], settings)
        self.assertEqual(it["hooks"], hooks)
        for rel in settings + hooks:
            with self.subTest(rel=rel):
                self.assertEqual(self.surfaces.files[rel].roles.get("interactive_session"), "run_shaping")
        for rel in hooks:
            self.assertIn("interactive_session", self.surfaces.files[rel].runs)
        planted, _ = _plant(hooks[0], 'DEFAULT_PROJECT_4131 = "CHORUS"')
        self.assertTrue(planted)
        self.assertTrue(all(h["violation"] and h["gates_in"] == SESSION_GATES for h in planted), planted)
        env, _ = _plant(".claude/settings.json", '  "env": {"D4D_MANIFEST": "data/preprocessed/CHORUS_manifest.yaml"},',
                        after="{")
        self.assertTrue(env)
        self.assertTrue(all(h["context"] == "code_table" and h["violation"] and h["gates_in"] == SESSION_GATES
                            for h in env), env)

    def test_an_evaluator_a_generation_closure_reaches_gates(self):
        """Evaluation is not exempt for being evaluation (#4131): the LLM
        evaluator `prepare_registration.py` imports from the package is in
        the native closure and its code tables gate there, a rubric agent's
        description gates in interactive sessions, and SKILL.md no longer
        says either never gates."""
        rel = "src/data_sheets_schema/evaluation/evaluate_d4d_llm.py"
        self.assertEqual(self.facts["model_clients"][rel]["classified"], "the api/native/deterministic import closure")
        self.assertEqual(self.surfaces.files[rel].roles, {"native_agentic": "run_shaping"})
        planted, _ = _plant(rel, "RUBRIC_HINTS_4131 = {'CHORUS': 'hospital EHR'}")
        self.assertTrue([h for h in planted if h["match"] == "CHORUS" and h["violation"]
                         and h["gates_in"] == ["native_agentic"]])
        rubric, _ = _plant(".claude/agents/d4d-rubric10.md", "  Example: score the CHORUS record.", after="description:")
        self.assertTrue(rubric and all(h["violation"] and h["gates_in"] == SESSION_GATES for h in rubric))
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("Evaluation is out of scope", skill)
        self.assertIn("evaluate_d4d_llm.py", skill)

    def test_controller_text_found_by_data_flow(self):
        """SYSTEM, returned by render_system, and command_guidance and
        lookup_guidance, passed to --system-prompt (#4054)."""
        text = self.facts["model_text"]
        for rel, label in (("notes/matched_cborg_2026-09-13/audit_controls/prepare.py", "SYSTEM"),
                           ("notes/matched_cborg_2026-09-13/finalization_controls/prepare.py", "SYSTEM"),
                           ("notes/matched_cborg_2026-09-13/native_controls/native_command_policy.py",
                            "command_guidance()"),
                           ("notes/matched_cborg_2026-09-13/native_controls/native_readonly.py", "lookup_guidance()")):
            with self.subTest(rel=rel):
                self.assertTrue(any(x.startswith(label) for x in text.get(rel, [])), text.get(rel))

    def test_data_flow_follows_a_system_prompt_through_calls_and_constants(self):
        """From `--system-prompt`: a function whose result is part of the
        prompt, the functions and module constants it returns, across an
        import; not a function whose result only parameterises a call."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes/exp_4054"
            _write(base / "launch.py", "from data_sheets_schema.api_runner import RunSpec\n"
                                       "from guidance import guide\nimport policy\n"
                                       "def main(cli):\n    pol = policy.choose(1)\n"
                                       "    prompt = HEAD + guide(pol)\n"
                                       "    return [cli, '--system-prompt', prompt]\n"
                                       "HEAD = 'You run one registered job.'\n")
            _write(base / "guidance.py", "BODY = 'Read only registered inputs.'\n"
                                         "def lookup():\n    return 'Use the Read tool.'\n"
                                         "def guide(policy):\n    return BODY + lookup()\n")
            _write(base / "policy.py", "WORDS = 'not model text'\ndef choose(n):\n    return WORDS\n")
            parsed = _parsed(root, "notes")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            spans = scan.model_text_spans(root, parsed, index, controllers)
        labels = {rel: sorted(label.split(" ")[0] for *_, label in sp) for rel, sp in spans.items()}
        self.assertEqual(labels, {"notes/exp_4054/launch.py": ["HEAD"],
                                  "notes/exp_4054/guidance.py": ["BODY", "guide()", "lookup()"]})

    def test_the_toolchain_hands_native_runs_no_python_file(self):
        """agentic_runtime.toolchain() lists `*.md` in .claude/commands and
        .claude/agents and the two schemas: no agent script reaches a native
        run that way (#4040, #4054). Cross-checked against the runtime."""
        from data_sheets_schema import agentic_runtime
        tc = self.facts["toolchain"]
        self.assertEqual((tc["pattern"], tc["recursive"]), ("*.md", False))
        resources = agentic_runtime.toolchain()["resources"]
        for name in resources:
            with self.subTest(name=name):
                self.assertTrue(name in tc["schemas"] or (name.endswith(".md") and
                                                          any(name.startswith(d + "/") for d in tc["directories"])))
        self.assertFalse([n for n in resources if n.endswith(".py")])

    def test_an_agent_script_is_a_surface_only_where_something_runs_or_imports_it(self):
        """No glob over .claude/agents/scripts (#4054): a script an exposed
        agent runs is exposed, and so is what it imports (#4091); a script
        the RO-Crate arm imports is deterministic; one nothing reaches is no
        surface. The field_prioritizer demo list sits in a __main__ block
        nothing runs: the arm and rocrate_to_d4d.py, which the exposed
        d4d-rocrate agent runs, only import it."""
        files = self.surfaces.files
        for rel in sorted(files):
            if rel.startswith(".claude/agents/scripts/"):
                with self.subTest(rel=rel):
                    self.assertIn(files[rel].roles.get("native_agentic"), (None, "exposed"))
        self.assertEqual(files[".claude/agents/scripts/schema_stats.py"].roles, {"native_agentic": "exposed"})
        prioritizer = files[".claude/agents/scripts/field_prioritizer.py"]
        self.assertEqual(prioritizer.roles, {"deterministic": "run_shaping", "native_agentic": "exposed"})
        self.assertEqual(prioritizer.runs, set())
        self.assertIn(".claude/agents/scripts/field_prioritizer.py",
                      self.facts["run_script_imports"][".claude/agents/scripts/rocrate_to_d4d.py"])
        self.assertNotIn(".claude/agents/scripts/generate_interface_mapping.py", files)

    def test_the_deterministic_arms_are_derived_from_the_code(self):
        """The arm commands are the CLI groups that name a non-baseline arm's
        bundle, and their surfaces are their import closure, followed
        through the directory setup_repo_imports puts on sys.path (#4054)."""
        self.assertEqual(set(self.facts["deterministic_commands"]),
                         {"src/data_sheets_schema/cli/healthsheet.py", "src/data_sheets_schema/cli/rocrate.py"})
        # The selected native renderer now imports the explicit runtime schema.
        # Its controller/authority dependencies add their actual frozen lookup
        # roots to this static closure, without running a native controller.
        self.assertEqual(self.facts["deterministic_sys_path"], [".claude/agents/scripts",
            "notes/claudecode_direct", "notes/matched_cborg_2026-09-13",
            "notes/matched_cborg_2026-09-13/native_controls"])
        closure = set(self.facts["deterministic_closure"])
        for module in ('native_shared_render', 'native_execution_registration',
                       'native_execution_authority', 'native_attribution_controller'):
            self.assertIn(f'src/data_sheets_schema/{module}.py', closure)
        for rel in ("src/data_sheets_schema/healthsheet.py", "src/data_sheets_schema/rocrate_normalize.py",
                    ".claude/agents/scripts/rocrate_to_d4d.py", ".claude/agents/scripts/field_prioritizer.py"):
            self.assertIn(rel, closure)
        self.assertEqual(self.surfaces.files["src/data_sheets_schema/healthsheet.py"].roles["deterministic"],
                         "model_facing")
        self.assertEqual(self.surfaces.files["src/data_sheets_schema/cli/healthsheet.py"].roles["deterministic"],
                         "run_shaping")

    def test_a_module_the_healthsheet_arm_imports_is_a_surface(self):
        """Text moved from healthsheet.py into a module it imports stays a
        deterministic surface: the closure is followed, not listed (#4054)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            shutil.copy(ROOT / scan.CLI_API, _write(root / scan.CLI_API, "").parent / "api.py")
            _write(root / "src/data_sheets_schema/cli/healthsheet.py",
                   "HELP = 'writes {PROJECT}_healthsheet_only.txt'\n"
                   "def main():\n    from data_sheets_schema.healthsheet import build\n")
            _write(root / "src/data_sheets_schema/healthsheet.py", "from data_sheets_schema.healthsheet_text import O\n")
            _write(root / "src/data_sheets_schema/healthsheet_text.py", "O = 'Origin: FAIRhub API record'\n")
            commands = scan.deterministic_arm_commands(root)
            closure, _ = scan._code_closure(root, [root / r for r in commands], set())
        self.assertEqual(list(commands), ["src/data_sheets_schema/cli/healthsheet.py"])
        self.assertIn("healthsheet_text.py", {p.name for p in closure})

    def test_the_upstream_input_is_what_the_download_group_imports(self):
        """The upstream input steps are the `src.download` modules the `d4d
        download` group imports, and an arm's closure stops there (#4054)."""
        self.assertEqual(set(self.facts["shared_input"]), {"src/download/concatenate_documents.py",
                                                           "src/download/organized_dataset_extractor.py",
                                                           "src/download/preprocess_sources.py"})
        for rel in self.facts["shared_input"]:
            self.assertNotIn(rel, self.facts["deterministic_closure"])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            _write(root / "src/data_sheets_schema/cli/arm_4054.py",
                   "def run():\n    from src.download.fetch_4054 import main\n"
                   "    from data_sheets_schema.helper_4054 import x\n")
            _write(root / "src/data_sheets_schema/helper_4054.py", "x = 1\n")
            upstream = _write(root / "src/download/fetch_4054.py", "PROJECTS = ['CHORUS']\n")
            closure, _ = scan._code_closure(root, [root / "src/data_sheets_schema/cli/arm_4054.py"],
                                            {upstream.resolve()})
            reached, _ = scan._code_closure(root, [root / "src/data_sheets_schema/cli/arm_4054.py"], set())
        self.assertEqual({p.name for p in closure}, {"arm_4054.py", "helper_4054.py"})
        self.assertIn("fetch_4054.py", {p.name for p in reached})

    def test_every_model_facing_module_is_in_a_discovered_closure(self):
        """MODEL_FACING_MODULES names top-level package modules; each is in
        the api, native or deterministic closure, matched by path so that
        cli/healthsheet.py does not stand in for healthsheet.py (#4054)."""
        closures = set(self.facts["api_closure"] + self.facts["native_closure"] + self.facts["deterministic_closure"])
        self.assertEqual(_missing_model_facing_modules(ROOT, closures), set())


#: A runner small enough to read (#4085): the request type, and a
#: `build_phase` that sends what a module the runner imports holds: a
#: constant read through the module, one a helper returns from a
#: function-level import, a function's result a helper's result is built
#: from, and one a serialization carries.
DERIVATION_RUNNER = '''from dataclasses import dataclass, field

from data_sheets_schema import phase_notes_4085


@dataclass
class PhaseRequest:
    phase: str
    system: str
    cached_blocks: list = field(default_factory=list)
    messages: list = field(default_factory=list)


def phase_instruction(phase):
    from data_sheets_schema.phase_notes_4085 import INSTRUCTION
    return INSTRUCTION


def framed(text):
    return "## " + text


def build_phase(spec, phase, *, carry):
    cached = [{"type": "text", "text": spec.bundle.read_text(), "cache_control": {"type": "ephemeral"}}]
    parts = list(cached)
    parts.append({"type": "text", "text": phase_notes_4085.NOTE})
    parts.append({"type": "text", "text": phase_instruction(phase)})
    parts.append({"type": "text", "text": framed(phase_notes_4085.role())})
    parts.append({"type": "text", "text": "".join(sorted(phase_notes_4085.details()))})
    return PhaseRequest(phase=phase, system=spec.system, cached_blocks=cached,
                        messages=[{"role": "user", "content": parts}])
'''
#: The new module: four sentences the runner sends and one it never does,
#: which gates only because the module as a whole is model-facing.
PHASE_NOTES = ('NOTE = "Describe the CHORUS cohort as its sites report it."\n'      # 1
               'INSTRUCTION = "Return the record of the VOICE release."\n'          # 2
               'ASIDE = "A CM4AI sentence this module never sends."\n'              # 3
               '\n\n'
               'def role():\n'                                                       # 6
               '    return "You describe the AI-READI release."\n'                  # 7
               '\n\n'
               'def details():\n'                                                    # 10
               '    return ["Cite the fairhub page."]\n')                           # 11
#: What reaches a request as something other than a module's own sentence
#: (#4085): a file's content (not the path a read is called on), a value
#: picked by a key (not the key), an identifier (a bare token, which gates
#: as code in any role), and a report written for a person (not a model
#: input). `prompts_4085` is the control: its sentence is sent.
PRECISION_RUNNER = '''from dataclasses import dataclass, field
from pathlib import Path

from data_sheets_schema import data_4085, ids_4085, paths_4085, prompts_4085, reports_4085


@dataclass
class PhaseRequest:
    phase: str
    system: str
    cached_blocks: list = field(default_factory=list)
    messages: list = field(default_factory=list)


def build_phase(spec, phase, *, carry):
    guide = paths_4085.locate(spec).read_text(encoding="utf-8")
    value = data_4085.rows(spec)["cohort"]
    reports_4085.write(spec.output)
    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,
                        messages=[{"role": "user", "content": [guide, value, ids_4085.label(spec)]}])
'''
PRECISION_MODULES = {
    "paths_4085": 'from pathlib import Path\n\n\ndef locate(spec):\n    return Path("data") / "CHORUS guide.md"\n',
    "data_4085": 'def rows(spec):\n    return {"CHORUS cohort": spec.value, "cohort": spec.other}\n',
    "ids_4085": 'def label(spec):\n    return "dataset-" + spec.key\n',
    "reports_4085": ('from pathlib import Path\n\nREPORT = "A CHORUS report written for a person."\n\n\n'
                     'def write(directory):\n    (Path(directory) / "report_4085.md").write_text(REPORT)\n'),
    "prompts_4085": 'SYSTEM = "You write records for one VOICE dataset."\n',
}
#: Listed in MODEL_FACING_MODULES, not reached by the derivation (#4085):
#: what they hand a model goes through a channel the data flow does not
#: read (SKILL.md, Limits) — a tool's output (`d4d download scope`), a file
#: a controller or a run writes for a later reader (a batch plan or index),
#: or data with no sentence of the module's own (manifest values, JSON
#: keys). The list is what keeps them model-facing; a change here is a
#: change to the cross-check, made on purpose.
LISTED_NOT_DERIVED = ["audit_batches", "audit_grammar", "audit_omissions", "evidence_assertions", "grounding",
                      "scope", "source_metadata", "typed_audit"]


class TestModelFacingDerivation(unittest.TestCase):
    """Which top-level `data_sheets_schema` modules write model-facing text
    is derived by data flow from the requests the runner builds, the
    model-input writes and the controllers' sinks; MODEL_FACING_MODULES is
    a cross-check (#4085)."""

    @staticmethod
    def _root(d: str, runner: str, modules: dict[str, str]) -> Path:
        root = Path(d).resolve()
        _write(root / scan.CLI_API, (ROOT / scan.CLI_API).read_text(encoding="utf-8"))
        _write(root / "src/data_sheets_schema/__init__.py", "")
        _write(root / scan.RUNNER, runner)
        for name, text in modules.items():
            _write(root / f"src/data_sheets_schema/{name}.py", text)
        return root

    @staticmethod
    def _derive(root: Path, *, sinks: bool = True):
        """The derivation over a scratch root, with its sinks or (`sinks`
        False) none: (derived modules, spans, the sinks' facts)."""
        parsed = _parsed(root, "src")
        index = scan._notes_index(root, parsed)
        found, facts = scan.model_input_sinks(root, parsed, index, [], set())
        spans, wrote = scan.text_flow(root, parsed, index, {}, found if sinks else [])
        return scan.derive_model_facing(wrote), spans, facts

    @staticmethod
    def _violations(root: Path, rel: str, derived, spans) -> set:
        """(token, line) of every violation in `rel` under the role and the
        spans the derivation gives it."""
        surface = scan.Surface(rel, ["api"], scan._module_role(root / rel, derived), "live", "t",
                               text_spans=list(spans.get(rel, [])))
        hits = scan.scan_file(root, surface, list(_tokens()))
        for h in hits:
            h["exception"] = None
        return {(h["match"], h["line"]) for h in hits if scan.is_violation(h)}

    def test_a_project_name_in_a_new_module_build_phase_sends_gates(self):
        """The planted case: NOTE reaches the request through `parts.append`,
        INSTRUCTION through a helper's function-level import, `role()`
        through the parameter `framed()`'s result is built from, and
        `details()` through `sorted`. The module is model-facing, so even
        the sentence it never sends gates; with the derivation off nothing
        in it does."""
        rel = "src/data_sheets_schema/phase_notes_4085.py"
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, DERIVATION_RUNNER, {"phase_notes_4085": PHASE_NOTES})
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            line = DERIVATION_RUNNER.splitlines().index("    return PhaseRequest(phase=phase, system=spec.system, "
                                                        "cached_blocks=cached,") + 1
            self.assertEqual(facts["requests"], [f"{scan.RUNNER}:{line}"])
            self.assertIn("phase_notes_4085", derived)
            # each sent sentence is found on its own route, ASIDE on none
            self.assertEqual({label.split(" ")[0] for *_, label in spans[rel]},
                             {"NOTE", "INSTRUCTION", "role()", "details()"})
            self.assertEqual(self._violations(root, rel, derived, spans),
                             {("CHORUS", 1), ("VOICE", 2), ("CM4AI", 3), ("AI-READI", 7), ("fairhub", 11)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("phase_notes_4085", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_text_moved_out_of_the_healthsheet_bundle_builder_still_gates(self):
        """The #4054 review scenario: healthsheet.py's Origin line moved into
        a new module it imports. The bundle it writes ends in the healthsheet
        arm's `_healthsheet_only.txt`, so what it writes is model input, and
        the new module is model-facing: the FAIRhub name there gates."""
        origin = '*([f"Origin: {origin}"] if origin else []),'
        text = (ROOT / "src/data_sheets_schema/healthsheet.py").read_text(encoding="utf-8")
        self.assertEqual(text.count(origin), 1)
        moved = text.replace(origin, "ORIGIN,").replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom data_sheets_schema.healthsheet_text import ORIGIN\n", 1)
        rel = "src/data_sheets_schema/healthsheet_text.py"
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, DERIVATION_RUNNER, {
                "healthsheet": moved, "healthsheet_text": 'ORIGIN = "Origin: FAIRhub API record, metadata.healthsheet"\n'})
            derived, spans, facts = self._derive(root)
            self.assertEqual([w.rsplit(":", 1)[0] for w in facts["writers"]], ["src/data_sheets_schema/healthsheet.py"])
            self.assertIn("healthsheet_text", derived)
            self.assertIn("healthsheet", derived)
            self.assertEqual(self._violations(root, rel, derived, spans), {("FAIRhub", 1)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("healthsheet_text", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_what_reaches_a_model_as_data_is_not_derived(self):
        """A file's content is not the path read to get it, a key picks a
        value without being one, an identifier is a bare token, and a report
        written for a person is not model input: none of those modules
        writes model-facing text. The module whose sentence is the system
        prompt does."""
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, PRECISION_RUNNER, PRECISION_MODULES)
            derived, spans, facts = self._derive(root)
        self.assertEqual(facts["writers"], [])
        self.assertIn("prompts_4085", derived)
        self.assertIn("src/data_sheets_schema/ids_4085.py", spans)      # reached, with no sentence of its own
        self.assertEqual({"paths_4085", "data_4085", "ids_4085", "reports_4085"} & set(derived), set())

    def test_imported_locator_constants_remain_non_text(self):
        """A locator's import spelling must not turn its bytes into model text."""



































        for expression, extra_import in (
            ("paths_4405.DOC_PATH", "from data_sheets_schema import paths_4405\n"),
            ("DOC_PATH", "from data_sheets_schema.paths_4405 import DOC_PATH\n"),
        ):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n", "from pathlib import Path\n" + extra_import)
                runner = runner.replace("paths_4085.locate(spec)", f"Path({expression})")
                modules = dict(PRECISION_MODULES)
                modules["paths_4405"] = 'DOC_PATH = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertNotIn("paths_4405", derived)
                self.assertEqual(set(), self._violations(
                    root, "src/data_sheets_schema/paths_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("paths_4405", off)

    def test_imported_lookup_key_constants_remain_non_text(self):
        for expression, extra_import in (
            ("keys_4405.SECTION_KEY", "from data_sheets_schema import keys_4405\n"),
            ("SECTION_KEY", "from data_sheets_schema.keys_4405 import SECTION_KEY\n"),
        ):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n", "from pathlib import Path\n" + extra_import)
                runner = runner.replace('"cohort"', expression)
                modules = dict(PRECISION_MODULES)
                modules["keys_4405"] = 'SECTION_KEY = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertNotIn("keys_4405", derived)
                self.assertEqual(set(), self._violations(
                    root, "src/data_sheets_schema/keys_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("keys_4405", off)

    def test_locator_and_key_constants_sent_as_text_still_derive(self):
        for expression, extra_import in (
            ("paths_4405.DOC_PATH", "from data_sheets_schema import paths_4405\n"),
            ("DOC_PATH", "from data_sheets_schema.paths_4405 import DOC_PATH\n"),
        ):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n", "from pathlib import Path\n" + extra_import)
                runner = runner.replace("paths_4085.locate(spec)", f"Path({expression})")
                runner = runner.replace(
                    "[guide, value, ids_4085.label(spec)]",
                    f"[guide, value, ids_4085.label(spec), {expression}]")
                modules = dict(PRECISION_MODULES)
                modules["paths_4405"] = 'DOC_PATH = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertIn("paths_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/paths_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("paths_4405", off)

    def test_serialized_dictionary_keys_are_actual_model_text(self):
        for expression, extra_import in (
            ("keys_4405.KEY", "from data_sheets_schema import keys_4405\n"),
            ("KEY", "from data_sheets_schema.keys_4405 import KEY\n"),
        ):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n", "from pathlib import Path\nimport json\n" + extra_import)
                runner = runner.replace(
                    "[guide, value, ids_4085.label(spec)]", f'[json.dumps({{{expression}: "value"}})]')
                modules = dict(PRECISION_MODULES)
                modules["keys_4405"] = 'KEY = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertIn("keys_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/keys_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("keys_4405", off)

    def test_joined_dictionary_keys_are_actual_model_text(self):
        for expression, extra_import in (
            ("keys_4405.KEY", "from data_sheets_schema import keys_4405\n"),
            ("KEY", "from data_sheets_schema.keys_4405 import KEY\n"),
        ):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n", "from pathlib import Path\n" + extra_import)
                runner = runner.replace(
                    "[guide, value, ids_4085.label(spec)]", f'[", ".join({{{expression}: "value"}}.keys())]')
                modules = dict(PRECISION_MODULES)
                modules["keys_4405"] = 'KEY = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertIn("keys_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/keys_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("keys_4405", off)

    def test_unknown_call_constants_keep_existing_conservative_propagation(self):
        for expression, extra_import in (
            ("constants_4405.VALUE", "from data_sheets_schema import constants_4405\n"),
            ("VALUE", "from data_sheets_schema.constants_4405 import VALUE\n"),
        ):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n",
                    "from pathlib import Path\nfrom external_pkg import transform\n" + extra_import)
                runner = runner.replace(
                    "[guide, value, ids_4085.label(spec)]", f"[transform({expression})]")
                modules = dict(PRECISION_MODULES)
                modules["constants_4405"] = 'VALUE = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertIn("constants_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/constants_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("constants_4405", off)

    def test_unambiguous_pathlib_constructor_import_aliases_preserve_selector_precision(self):
        for import_stmt, ctor in (
            ("import pathlib as pl\n", "pl.Path"),
            ("from pathlib import Path as LocalPath\n", "LocalPath"),
            ("from pathlib import PurePath as LocalPurePath\n", "LocalPurePath"),
        ):
            with self.subTest(ctor=ctor), tempfile.TemporaryDirectory() as d:
                runner = PRECISION_RUNNER.replace(
                    "from pathlib import Path\n",
                    "from pathlib import Path\n" + import_stmt + "from data_sheets_schema import paths_4405\n")
                runner = runner.replace(
                    'paths_4085.locate(spec).read_text(encoding="utf-8")',
                    f'{ctor}(paths_4405.DOC_PATH).read_text(encoding="utf-8")')
                modules = dict(PRECISION_MODULES)
                modules["paths_4405"] = 'DOC_PATH = "Describe the VOICE cohort."\n'
                root = self._root(d, runner, modules)
                derived, spans, _ = self._derive(root)
                self.assertNotIn("paths_4405", derived)

    def _parameter_client_fixture(self, directory, helper_source, call_expr, extra_imports=""):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import client_4405\n")
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "[client_4405.run()]")
        modules = dict(PRECISION_MODULES)
        modules["reader_4405"] = helper_source
        modules["client_4405"] = (
            'ASIDE = "A VOICE aside this module never sends."\n'
            "from data_sheets_schema import reader_4405\n" + extra_imports +
            "def run():\n    return " + call_expr + "\n")
        root = self._root(directory, runner, modules)
        return (root, *self._derive(root)[:2])

    def _parameter_cycle_argument_fixture(self, directory, helper_source, call_expr, extra_imports=""):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import client_4405\n")
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "[client_4405.run()]")
        modules = dict(PRECISION_MODULES)
        modules["arguments_4405"] = (
            'ARG = "Describe the VOICE cohort."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        modules["reader_4405"] = helper_source
        modules["client_4405"] = (
            "from data_sheets_schema import reader_4405\n" + extra_imports +
            "def run():\n    return " + call_expr + "\n")
        root = self._root(directory, runner, modules)
        return (root, *self._derive(root)[:2])

    def test_resolved_file_reader_parameter_is_not_returned_text(self):
        helper = "from pathlib import Path\n\ndef read_doc(path):\n    return Path(path).read_text()\n"
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._parameter_client_fixture(d, helper, 'reader_4405.read_doc("cohort.txt")')
            self.assertNotIn("client_4405", derived)
            self.assertEqual(set(), self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans))

    def test_resolved_lookup_parameter_is_not_returned_text(self):
        helper = 'TABLE = {"cohort": "value"}\n\ndef lookup(key):\n    return TABLE[key]\n'
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._parameter_client_fixture(d, helper, 'reader_4405.lookup("cohort")')
            self.assertNotIn("client_4405", derived)
            self.assertEqual(set(), self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans))

    def test_resolved_wrapper_preserves_locator_only_parameter_use(self):
        helper = (
            "from pathlib import Path\n\n"
            "def inner(path):\n    return Path(path).read_text()\n\n"
            "def outer(doc):\n    return inner(doc)\n")
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._parameter_client_fixture(d, helper, 'reader_4405.outer("cohort.txt")')
            self.assertNotIn("client_4405", derived)
            self.assertEqual(set(), self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans))

    def test_resolved_text_parameter_still_derives_its_literal_caller(self):
        helper = 'def render(label):\n    return f"Section: {label}"\n'
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._parameter_client_fixture(
                d, helper, 'reader_4405.render("Describe the VOICE cohort.")')
            self.assertIn("client_4405", derived)
            self.assertIn(("VOICE", 4), self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans))

    def test_mixed_file_locator_and_emitted_parameter_remains_text(self):
        helper = (
            "from pathlib import Path\n\n"
            "def read_with_header(path):\n    return f'{path}: {Path(path).read_text()}'\n")
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._parameter_client_fixture(
                d, helper, 'reader_4405.read_with_header("Describe the VOICE cohort.")')
            self.assertIn("client_4405", derived)
            self.assertIn(("VOICE", 4), self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans))

    def test_non_text_and_text_uses_do_not_poison_each_other_in_either_order(self):
        helper = (
            "from pathlib import Path\n\n"
            "def locate_and_echo(loc, echoed):\n    return Path(loc).read_text() + echoed\n")
        for expr in (
            'reader_4405.locate_and_echo(arguments_4405.ARG, "Describe the CM4AI cohort.")',
            'reader_4405.locate_and_echo(echoed="Describe the CM4AI cohort.", loc=arguments_4405.ARG)',
        ):
            with self.subTest(expr=expr), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, expr, "from data_sheets_schema import arguments_4405\n")
                self.assertIn("client_4405", derived)
                self.assertNotIn("arguments_4405", derived)
                self.assertEqual({("CM4AI", 4)}, self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans))

    def test_resolved_selector_parameters_do_not_promote_imported_arguments(self):
        helper = "from pathlib import Path\n\ndef read_doc(path):\n    return Path(path).read_text()\n"
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertNotIn("arguments_4405", derived)

    def test_mutual_wrapper_cycle_keeps_only_selector_arguments_in_both_definition_orders(self):
        a = "def cycle_a(path):\n    return cycle_b(path)\n"
        b = "def cycle_b(path):\n    return Path(path).read_text() if path else cycle_a(path)\n"
        for helper in ("from pathlib import Path\n\n" + a + b, "from pathlib import Path\n\n" + b + a):
            with self.subTest(helper=helper), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.cycle_a(arguments_4405.ARG)", "from data_sheets_schema import arguments_4405\n")
                self.assertNotIn("arguments_4405", derived)

    def test_text_in_mutual_wrapper_cycle_wins_over_selector_use_in_both_orders(self):
        a = "def cycle_a(path):\n    return cycle_b(path)\n"
        b = "def cycle_b(path):\n    return Path(path).read_text() + path if path else cycle_a(path)\n"
        for helper in ("from pathlib import Path\n\n" + a + b, "from pathlib import Path\n\n" + b + a):
            for argument, imports in (
                ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
                ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
            ):
                with self.subTest(helper=helper, argument=argument), tempfile.TemporaryDirectory() as d:
                    root, derived, spans = self._parameter_cycle_argument_fixture(
                        d, helper, "reader_4405.cycle_a(" + argument + ")", imports)
                    self.assertIn("arguments_4405", derived)
                    self.assertIn(("VOICE", 2), self._violations(
                        root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                    off, _, _ = self._derive(root, sinks=False)
                    self.assertNotIn("arguments_4405", off)

    def test_explicit_named_keyword_selector_supports_keyword_only_and_kwargs_formals(self):
        helpers = (
            'from pathlib import Path\n\ndef read_doc(*, path):\n    return Path(path).read_text()\n',
            'from pathlib import Path\n\ndef read_doc(**options):\n    return Path(options["path"]).read_text()\n',
        )
        for helper in helpers:
            with self.subTest(helper=helper), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(path=arguments_4405.ARG)",
                    "from data_sheets_schema import arguments_4405\n")
                self.assertNotIn("arguments_4405", derived)
                self.assertNotIn("client_4405", derived)
                self.assertNotIn(("VOICE", 2), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))

    def test_variadic_text_arguments_remain_model_text_with_explicit_and_starred_actuals(self):
        cases = (
            ('def emit(*parts):\n    return " ".join(parts)\n',
             'reader_4405.emit("CHORUS cohort")'),
            ('def emit(*parts):\n    return " ".join(parts)\n',
             'reader_4405.emit(*("CHORUS cohort",))'),
            ('def emit(**parts):\n    return " ".join(parts.values())\n',
             'reader_4405.emit(note="CHORUS cohort")'),
            ('def emit(**parts):\n    return " ".join(parts.values())\n',
             'reader_4405.emit(**{"note": "CHORUS cohort"})'),
        )
        for helper, expression in cases:
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_client_fixture(d, helper, expression)
                self.assertIn("client_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/client_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("client_4405", off)

    def test_unresolved_parameter_call_stays_conservative_beside_a_selector_use(self):
        helper = ('from pathlib import Path\nfrom external_formatter import format_value\n\n'
                  'def read_doc(path):\n    return Path(path).read_text() + format_value(path)\n')
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)

    def test_decorated_selector_body_does_not_suppress_actual_argument_text(self):
        helper = ('from pathlib import Path\n\n'
                  'def emit_argument(fn):\n'
                  '    def wrapped(path):\n        return path\n'
                  '    return wrapped\n\n'
                  '@emit_argument\ndef read_doc(path):\n'
                  '    return Path(path).read_text()\n')
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 2), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)

    def test_module_rebinding_does_not_suppress_actual_argument_text(self):
        helper = ('from pathlib import Path\n\n'
                  'def read_doc(path):\n    return Path(path).read_text()\n\n'
                  'def emit_argument(fn):\n'
                  '    def wrapped(path):\n        return path\n'
                  '    return wrapped\n\n'
                  'read_doc = emit_argument(read_doc)\n')
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 2), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)

    def test_later_unresolved_import_keeps_conservative_argument_coverage(self):
        helper = ('from pathlib import Path\n\n'
                  'def read_doc(path):\n    return Path(path).read_text()\n\n'
                  'from external_formatter import emit as read_doc\n')
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)

    def test_formal_writes_do_not_hide_selector_arguments_that_are_emitted(self):
        cases = (
            ("assignment", 'def read_doc(path, echoed=""):\n'
             '    echoed = path\n'
             '    return Path(path).read_text() + echoed\n', ''),
            ("augmentation", 'def read_doc(path, echoed=""):\n'
             '    echoed += path\n'
             '    return Path(path).read_text() + echoed\n', ', "prefix "'),
            ("named_expression", 'def read_doc(path, echoed=""):\n'
             '    (echoed := path)\n'
             '    return Path(path).read_text() + echoed\n', ''),
            ("append", 'def read_doc(path, echoed=None):\n'
             '    echoed = []\n    echoed.append(path)\n'
             '    return Path(path).read_text() + str(echoed)\n', ''),
            ("item", 'def read_doc(path, echoed=None):\n'
             '    echoed = {}\n    echoed["key"] = path\n'
             '    return Path(path).read_text() + str(echoed)\n', ''),
            ("alias_append", 'def read_doc(path, echoed=None):\n'
             '    echoed = []\n    alias = echoed\n    alias.append(path)\n'
             '    return Path(path).read_text() + str(echoed)\n', ''),
        )
        for label, body, additional_actual in cases:
            for argument, imports in (
                ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
                ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
            ):
                with self.subTest(write=label, argument=argument), tempfile.TemporaryDirectory() as d:
                    root, derived, spans = self._parameter_cycle_argument_fixture(
                        d, 'from pathlib import Path\n\n' + body,
                        "reader_4405.read_doc(" + argument + additional_actual + ")", imports)
                    self.assertIn("arguments_4405", derived)
                    self.assertIn(("VOICE", 2), self._violations(
                        root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                    off, _, _ = self._derive(root, sinks=False)
                    self.assertNotIn("arguments_4405", off)

    def test_formal_scalar_writes_used_only_as_locators_remain_selectors(self):
        cases = (
            ('def read_doc(path, selected=""):\n'
             '    selected = path\n'
             '    return Path(selected).read_text()\n'),
            ('def read_doc(path, selected=""):\n'
             '    selected += path\n'
             '    return Path(selected).read_text()\n'),
        )
        for helper in cases:
            for argument, imports in (
                ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
                ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
            ):
                with self.subTest(helper=helper, argument=argument), tempfile.TemporaryDirectory() as d:
                    root, derived, spans = self._parameter_cycle_argument_fixture(
                        d, "from pathlib import Path\n\n" + helper, "reader_4405.read_doc(" + argument + ")", imports)
                    self.assertNotIn("arguments_4405", derived)
                    self.assertEqual(set(), self._violations(
                        root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                    off, _, _ = self._derive(root, sinks=False)
                    self.assertNotIn("arguments_4405", off)

    def test_name_augmentation_through_a_formal_alias_keeps_emitted_argument_text(self):
        helper = ('def echo_doc(path):\n'
                  '    alias = path\n'
                  '    alias += ""\n'
                  '    return alias\n')
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.echo_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)
                self.assertNotIn("client_4405", off)

    def test_uncertain_discarded_helper_effects_stay_conservative_through_a_locator_wrapper(self):
        """Discarded calls with unknown effects inside a locator wrapper keep argument coverage."""
        helper = (
            "from pathlib import Path\n"
            "from external_audit import record\n\n"
            "def step(path):\n"
            "    record(path)\n"
            "    return path\n\n"
            "def read_doc(path):\n"
            "    step(path)\n"
            "    return Path(path).read_text()\n"
        )
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)
                parsed = _parsed(root, "src")
                index = scan._notes_index(root, parsed)
                sinks, _ = scan.model_input_sinks(
                    root,
                    parsed,
                    index,
                    [{
                            "context_limit_tokens": 1000000, "context_limit_basis": "synthetic scanner test",
                            "model": "gpt-5",
                    }],
                    set(),
                )
                self.assertTrue(sinks)
                self.assertIn("arguments_4405", derived)
                self.assertNotIn("reader_4405", derived)
                self.assertNotIn("client_4405", derived)
                self.assertEqual(
                    self._violations(root, "src/data_sheets_schema/client_4405.py", derived, spans),
                    set(),
                )

    def test_consumed_resolved_helper_mutation_cannot_hide_argument_emitted_through_alias(self):
        """The result is a locator, but the same call mutates emitted list contents."""
        effect = ('def fill(items, path):\n'
                  '    items += [path]\n    return path\n\n')
        reader = ('def read_doc(path, echoed=None):\n'
                  '    echoed = []\n    selected = fill(echoed, path)\n'
                  '    return Path(selected).read_text() + f"{echoed}"\n\n')
        for reverse_definitions in (False, True):
            helper = 'from pathlib import Path\n\n' + (
                reader + effect if reverse_definitions else effect + reader)
            for argument, imports in (
                ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
                ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
            ):
                with self.subTest(reverse=reverse_definitions, argument=argument), tempfile.TemporaryDirectory() as d:
                    root, derived, spans = self._parameter_cycle_argument_fixture(
                        d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                    self.assertIn("arguments_4405", derived)
                    self.assertIn(("VOICE", 2), self._violations(
                        root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                    off, _, _ = self._derive(root, sinks=False)
                    self.assertNotIn("arguments_4405", off)

    def test_known_effectful_read_text_attribute_does_not_gain_file_reader_exemption(self):
        """A helper named read_text mutates text that its caller actually emits."""
        helper = ('from pathlib import Path\n'
                  'from data_sheets_schema import reader_4405 as own_reader\n\n'
                  'def read_text(items, path):\n'
                  '    items += [path]\n    return path\n\n'
                  'def read_doc(path, echoed=None):\n'
                  '    echoed = []\n    selected = own_reader.read_text(echoed, path)\n'
                  '    return Path(selected).read_text() + f"{echoed}"\n')
        for argument, imports in (
            ("arguments_4405.ARG", "from data_sheets_schema import arguments_4405\n"),
            ("ARG", "from data_sheets_schema.arguments_4405 import ARG\n"),
        ):
            with self.subTest(argument=argument), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._parameter_cycle_argument_fixture(
                    d, helper, "reader_4405.read_doc(" + argument + ")", imports)
                self.assertIn("arguments_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/arguments_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("arguments_4405", off)

    def _text_helper_alias_fixture_4733(self, directory, source):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import aliased_text_4405\n",
        )
        runner = runner.replace(
            "[guide, value, ids_4085.label(spec)]",
            "[aliased_text_4405.content()]",
        )
        modules = dict(PRECISION_MODULES)
        modules["aliased_text_4405"] = 'ASIDE = "A VOICE aside this function never sends."\n' + source
        root = self._root(directory, runner, modules)
        return (root, *self._derive(root)[:2])

    def test_imported_text_helper_aliases_derive_inline_sentence_modules_4733(self):
        """Aliased json/yaml/textwrap text helpers still promote inline prose."""
        for library, function, alias in (
            ("json", "dumps", "render_json"),
            ("yaml", "safe_dump", "render_yaml"),
            ("textwrap", "dedent", "trim_block"),
        ):
            for scope in ("module", "local"):
                with self.subTest(library=library, scope=scope), tempfile.TemporaryDirectory() as d:
                    imported = "from " + library + " import " + function + " as " + alias
                    expression = alias + '("Neutral instruction sentence")'
                    if scope == "module":
                        source = imported + "\n\ndef content():\n    return " + expression + "\n"
                    else:
                        source = "def content():\n    " + imported + "\n    return " + expression + "\n"
                    root, derived, spans = self._text_helper_alias_fixture_4733(d, source)
                    self.assertIn("aliased_text_4405", derived)
                    self.assertIn(("VOICE", 1), self._violations(
                        root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))
                    off, off_spans, _ = self._derive(root, sinks=False)
                    self.assertNotIn("aliased_text_4405", off)
                    self.assertEqual(set(), self._violations(
                        root, "src/data_sheets_schema/aliased_text_4405.py", off, off_spans))

    def test_module_aliased_text_helpers_keep_inline_sentence_derivation_4733(self):
        """import json as formatter still promotes formatter.dumps prose."""
        for library, function in (("json", "dumps"), ("yaml", "safe_dump"), ("textwrap", "dedent")):
            with self.subTest(library=library), tempfile.TemporaryDirectory() as d:
                source = ("import " + library + " as formatter\n\ndef content():\n"
                          "    return formatter." + function + '("Neutral instruction sentence")\n')
                root, derived, spans = self._text_helper_alias_fixture_4733(d, source)
                self.assertIn("aliased_text_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))

    def test_shadowed_text_helper_imports_do_not_bless_selector_arguments_4733(self):
        """A same-spelled function, assignment, or formal overrides the library import."""
        cases = (
            ("function", 'from pathlib import Path\nfrom json import dumps as render_json\n'
             '\ndef render_json(path):\n    return Path("source.txt").read_text()\n'
             '\ndef content():\n    return render_json("Neutral instruction sentence")\n'),
            ("assignment", 'from pathlib import Path\nfrom json import dumps as render_json\n'
             '\ndef read_document(path):\n    return Path(path).read_text()\n'
             '\nrender_json = read_document\n'
             '\ndef content():\n    return render_json("Neutral instruction sentence")\n'),
            ("parameter", 'from pathlib import Path\nfrom json import dumps as render_json\n'
             '\ndef read_document(path):\n    return Path(path).read_text()\n'
             '\ndef content(render_json=read_document):\n'
             '    return render_json("Neutral instruction sentence")\n'),
        )
        for binding, source in cases:
            with self.subTest(binding=binding), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._text_helper_alias_fixture_4733(d, source)
                self.assertNotIn("aliased_text_4405", derived)
                self.assertNotIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))

    def test_a_rendering_function_a_controller_calls_writes_model_text(self):
        """The native audit batch writes each child's instruction from
        `audit_batch_context.render_worker_context` into a file its launch
        hands the child: a function of another module that a controller
        calls, named for the text it renders, is model text, and its module
        is model-facing. A function named otherwise is not followed."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            _write(root / "notes/exp_4085/launch.py",
                   "from data_sheets_schema.api_runner import RunSpec\n"
                   "from data_sheets_schema import batch_text_4085\n\n\n"
                   "def prepare(path):\n"
                   "    path.write_text(batch_text_4085.render_child_context(RunSpec))\n"
                   "    path.with_suffix('.json').write_text(batch_text_4085.summary())\n")
            _write(root / "src/data_sheets_schema/batch_text_4085.py",
                   'DUTIES = "Audit every CHORUS path you are assigned."\n\n\n'
                   'def render_child_context(spec):\n    return DUTIES\n\n\n'
                   'def summary():\n    return "A VOICE summary for a person."\n')
            parsed = _parsed(root, "notes", "src")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            spans, wrote = scan.text_flow(root, parsed, index, controllers)
        self.assertEqual(set(controllers), {"notes/exp_4085/launch.py"})
        self.assertEqual(list(scan.derive_model_facing(wrote)), ["batch_text_4085"])
        self.assertEqual({label.split(" ")[0] for *_, label in spans["src/data_sheets_schema/batch_text_4085.py"]},
                         {"DUTIES", "render_child_context()"})

    def test_this_checkouts_derivation_and_the_hand_kept_list_agree(self):
        """Every module the derivation finds is on the list, and the list
        names no module the derivation misses beyond LISTED_NOT_DERIVED; every
        derived module is in a generation closure."""
        mf = _discovered()[1]["model_facing_modules"]
        self.assertEqual(mf["listed"], sorted(scan.MODEL_FACING_MODULES))
        self.assertEqual(mf["derived_not_listed"], [])
        self.assertEqual(mf["derived_outside_closures"], [])
        self.assertEqual(mf["listed_not_derived"], LISTED_NOT_DERIVED)
        self.assertEqual(set(mf["derived"]) | set(LISTED_NOT_DERIVED), scan.MODEL_FACING_MODULES)

    def test_the_requests_and_the_model_input_writes_are_derived(self):
        """The request type is what `build_phase` returns, and every
        construction of it is a sink; the bundle and chunk-manifest writers
        and the upstream input steps' writes are sinks; the runner's own
        writes (records, receipts) are not model input."""
        mi = _discovered()[1]["model_input"]
        self.assertEqual(mi["request"], {"class": "PhaseRequest", "fields": ["phase", "system", "cached_blocks",
                                                                             "messages"],
                                         "text_fields": list(scan.REQUEST_TEXT_FIELDS)})
        self.assertLessEqual({scan.RUNNER, "src/data_sheets_schema/receipt_completion.py",
                              "src/data_sheets_schema/removal_repair.py",
                              "src/data_sheets_schema/typed_audit_runtime.py"},
                             {r.rsplit(":", 1)[0] for r in mi["requests"]})
        self.assertLessEqual({"_chunks.yaml", "_crate_only.txt", "_healthsheet_only.txt", "_preprocessed.txt",
                              "_preprocessed_with_crate.txt"}, set(mi["model_input_files"]))
        writers = {w.rsplit(":", 1)[0] for w in mi["writers"]}
        self.assertLessEqual({"src/data_sheets_schema/chunking.py", "src/data_sheets_schema/healthsheet.py",
                              "src/data_sheets_schema/rocrate_normalize.py", "src/download/concatenate_documents.py",
                              "src/download/preprocess_sources.py"}, writers)
        self.assertNotIn(scan.RUNNER, writers)

    def test_rereceipt_gates_by_the_derivation_alone(self):
        """The live case the hand list missed: the renderer-24 receipt turn
        sends rereceipt's INSTRUCTION, HEADER and POLICY. Derived, it is
        model-facing whether or not the list names it, so a project name in
        any of its sentences gates; with neither, a sentence outside the
        text the flow follows does not."""
        surfaces, facts = _discovered()
        derived = facts["model_facing_modules"]["derived"]
        rel = "src/data_sheets_schema/rereceipt.py"
        self.assertIn("rereceipt", derived)
        self.assertEqual(surfaces.files[rel].roles["api"], "model_facing")
        unlisted = scan.MODEL_FACING_MODULES - {"rereceipt"}
        line = 'NOTE_4085 = "Describe the CHORUS cohort."'
        with mock.patch.object(scan, "MODEL_FACING_MODULES", unlisted):
            role = scan._module_role(ROOT / rel, derived)
            off = scan._module_role(ROOT / rel, {})
        self.assertEqual((role, off), ("model_facing", "run_shaping"))
        planted, _ = _plant(rel, line, surface=scan.Surface(rel, ["api"], role, "live", "t"))
        self.assertTrue(planted and all(h["violation"] and h["gates_in"] == ["api"] for h in planted), planted)
        quiet, _ = _plant(rel, line, surface=scan.Surface(rel, ["api"], off, "live", "t"))
        self.assertTrue(quiet and not any(h["violation"] for h in quiet), quiet)


    def _discarded_container_effect_fixture(self, directory, mutation, helper, extra_import):
        """A real request receives a list populated before its construction."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n", "from pathlib import Path\n" + extra_import)
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, "    parts = []\n" + mutation + "\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        modules = dict(PRECISION_MODULES)
        modules["container_effect_4405"] = helper
        modules["hidden_policy_4405"] = (
            'SYSTEM = "Describe the CHORUS cohort from its source records."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        root = self._root(directory, runner, modules)
        derived, spans, facts = self._derive(root)
        self.assertEqual(facts["request"]["class"], "PhaseRequest")
        self.assertEqual(len(facts["requests"]), 1)
        self.assertIn("prompts_4085", derived)
        return root, derived, spans

    def test_discarded_resolved_helper_mutation_reaches_preconstruction_request_text(self):
        """A discarded return does not discard mutations of the emitted container."""
        cases = (
            ("helper_constant",
             "    effects.add_policy(parts)",
             'from data_sheets_schema import hidden_policy_4405 as policy\n\n'
             'def add_policy(items):\n    items.append(policy.SYSTEM)\n',
             "from data_sheets_schema import container_effect_4405 as effects\n"),
            ("caller_and_formal_alias",
             "    destination = parts\n    put(destination=destination)",
             'from data_sheets_schema.hidden_policy_4405 import SYSTEM as statement\n\n'
             'def add_policy(*, destination):\n'
             '    target = destination\n    target.append(statement)\n',
             "from data_sheets_schema.container_effect_4405 import add_policy as put\n"),
            ("actual_text_argument",
             "    effects.add_policy(parts, text=policy.SYSTEM)",
             'def add_policy(items, text):\n    items.append(text)\n',
             "from data_sheets_schema import container_effect_4405 as effects\n"
             "from data_sheets_schema import hidden_policy_4405 as policy\n"),
        )
        for label, mutation, helper, imports in cases:
            with self.subTest(route=label), tempfile.TemporaryDirectory() as d:
                root, derived, spans = self._discarded_container_effect_fixture(
                    d, mutation, helper, imports)
                self.assertIn("hidden_policy_4405", derived)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/hidden_policy_4405.py", derived, spans),
                    {("CHORUS", 1), ("VOICE", 2)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("hidden_policy_4405", off)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/hidden_policy_4405.py", off, off_spans), set())

    def test_direct_preconstruction_container_append_keeps_the_same_text_control(self):
        """The same policy is already handled when append is in the request builder."""
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._discarded_container_effect_fixture(
                d, "    parts.append(policy.SYSTEM)", "",
                "from data_sheets_schema import hidden_policy_4405 as policy\n")
            self.assertIn("hidden_policy_4405", derived)
            self.assertEqual(self._violations(
                root, "src/data_sheets_schema/hidden_policy_4405.py", derived, spans),
                {("CHORUS", 1), ("VOICE", 2)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("hidden_policy_4405", off)
            self.assertEqual(self._violations(
                root, "src/data_sheets_schema/hidden_policy_4405.py", off, off_spans), set())

    def test_inline_emitted_mapping_keys_derive_their_source_module(self):
        """Serialization and key/item views emit inline keys, not only constants."""
        for key in ('"Neutral instruction sentence"', 'f"Neutral instruction {spec.label}"'):
            mapping = "{" + key + ": None}"
            for expression in (
                "json.dumps(" + mapping + ")",
                '" ".join(' + mapping + ".keys())",
                "json.dumps(list(" + mapping + ".items()))",
            ):
                with self.subTest(key=key, expression=expression), tempfile.TemporaryDirectory() as d:
                    runner = PRECISION_RUNNER.replace(
                        "from pathlib import Path\n",
                        "from pathlib import Path\nfrom data_sheets_schema import inline_keys_trace\n")
                    runner = runner.replace(
                        "[guide, value, ids_4085.label(spec)]", "[inline_keys_trace.content(spec)]")
                    modules = dict(PRECISION_MODULES)
                    modules["inline_keys_trace"] = (
                        'ASIDE = "A VOICE aside this function never sends."\n'
                        'import json\n\n'
                        'def content(spec):\n    return ' + expression + '\n')
                    root = self._root(d, runner, modules)
                    derived, spans, facts = self._derive(root)
                    self.assertTrue(facts["requests"])
                    self.assertIn("prompts_4085", derived)
                    self.assertIn("inline_keys_trace", derived)
                    rel = "src/data_sheets_schema/inline_keys_trace.py"
                    self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 1)})
                    off, off_spans, _ = self._derive(root, sinks=False)
                    self.assertNotIn("inline_keys_trace", off)
                    self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_inline_lookup_mapping_keys_remain_selectors(self):
        """A lookup emits its selected value, not its inline key or mapping keys."""
        for key in ('"Neutral instruction sentence"', 'f"Neutral instruction {spec.label}"'):
            for expression in (
                "spec.values[" + key + "]",
                "{" + key + ": spec.value}[" + key + "]",
            ):
                with self.subTest(key=key, expression=expression), tempfile.TemporaryDirectory() as d:
                    runner = PRECISION_RUNNER.replace(
                        "from pathlib import Path\n",
                        "from pathlib import Path\nfrom data_sheets_schema import inline_keys_trace\n")
                    runner = runner.replace(
                        "[guide, value, ids_4085.label(spec)]", "[inline_keys_trace.content(spec)]")
                    modules = dict(PRECISION_MODULES)
                    modules["inline_keys_trace"] = (
                        'ASIDE = "A VOICE aside this function never sends."\n\n'
                        'def content(spec):\n    return ' + expression + '\n')
                    root = self._root(d, runner, modules)
                    derived, spans, facts = self._derive(root)
                    self.assertTrue(facts["requests"])
                    self.assertIn("prompts_4085", derived)
                    self.assertNotIn("inline_keys_trace", derived)
                    self.assertEqual(self._violations(
                        root, "src/data_sheets_schema/inline_keys_trace.py", derived, spans), set())


    def _inline_key_context_fixture(self, directory, body, extra_modules=None):
        """A real request consumes content built from mappings in one new module."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import key_context_trace\n")
        runner = runner.replace(
            "[guide, value, ids_4085.label(spec)]", "[key_context_trace.content(spec)]")
        modules = dict(PRECISION_MODULES)
        modules["key_context_trace"] = (
            'ASIDE = "A VOICE aside this function never sends."\n'
            'import json\n'
            'from data_sheets_schema import key_factory_trace\n\n'
            'def content(spec):\n' + body + '\n')
        modules["key_factory_trace"] = ""
        modules.update(extra_modules or {})
        return self._root(directory, runner, modules)

    def test_inline_mapping_lookup_and_emission_are_order_independent(self):
        """Looking up a local mapping cannot consume its later emitted-key visit."""
        for key in ('"Neutral instruction sentence"', 'f"Neutral instruction {spec.label}"'):
            for emission_first in (False, True):
                with self.subTest(key=key, emission_first=emission_first), tempfile.TemporaryDirectory() as d:
                    expressions = ["mapping[" + key + "]", "json.dumps(mapping)"]
                    if emission_first:
                        expressions.reverse()
                    body = "    mapping = {" + key + ": spec.value}\n"
                    body += "    return (" + ", ".join(expressions) + ")"
                    root = self._inline_key_context_fixture(d, body)
                    derived, spans, facts = self._derive(root)
                    self.assertTrue(facts["requests"])
                    self.assertIn("key_context_trace", derived)
                    rel = "src/data_sheets_schema/key_context_trace.py"
                    self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 1)})
                    off, off_spans, _ = self._derive(root, sinks=False)
                    self.assertNotIn("key_context_trace", off)
                    self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_returned_mapping_projection_keeps_lookup_and_emission_distinct(self):
        """The same resolved factory needs separate lookup and emission visits."""
        factory = ('ASIDE = "A VOICE aside this function never sends."\n\n'
                   'def build_map(spec):\n'
                   '    return {"Neutral instruction sentence": spec.value}\n')
        lookup = 'key_factory_trace.build_map(spec)["Neutral instruction sentence"]'
        emission = 'json.dumps(key_factory_trace.build_map(spec))'
        for label, expression, expected in (
            ("lookup_only", lookup, False),
            ("lookup_then_emission", "(" + lookup + ", " + emission + ")", True),
            ("emission_then_lookup", "(" + emission + ", " + lookup + ")", True),
        ):
            with self.subTest(route=label), tempfile.TemporaryDirectory() as d:
                root = self._inline_key_context_fixture(
                    d, "    return " + expression, {"key_factory_trace": factory})
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertEqual("key_factory_trace" in derived, expected)
                rel = "src/data_sheets_schema/key_factory_trace.py"
                self.assertEqual(self._violations(root, rel, derived, spans),
                                 {("VOICE", 1)} if expected else set())
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_factory_trace", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_selected_nested_mapping_emits_keys_but_values_view_does_not(self):
        """A lookup removes one key layer, while values() removes its own keys."""
        for label, expression, expected in (
            ("selected_nested_map",
             'json.dumps({"slot": {"Neutral instruction sentence": None}}["slot"])', True),
            ("values_only",
             'json.dumps(list({"Neutral instruction sentence": spec.value}.values()))', False),
        ):
            with self.subTest(route=label), tempfile.TemporaryDirectory() as d:
                root = self._inline_key_context_fixture(d, "    return " + expression)
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertEqual("key_context_trace" in derived, expected)
                rel = "src/data_sheets_schema/key_context_trace.py"
                self.assertEqual(self._violations(root, rel, derived, spans),
                                 {("VOICE", 1)} if expected else set())
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_context_trace", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def _effect_contract_root_4733(self, directory, mutation, helper):
        """Build the actual preconstruction request with two independent text sources."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from data_sheets_schema import effect_contract_4733 as effects\n"
            "from data_sheets_schema import effect_source_one_4733 as one\n"
            "from data_sheets_schema import effect_source_two_4733 as two\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, mutation + "\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        modules = dict(PRECISION_MODULES)
        modules["effect_contract_4733"] = helper
        modules["effect_source_one_4733"] = (
            'TEXT = "First neutral instruction sentence."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        modules["effect_source_two_4733"] = (
            'TEXT = "Second neutral instruction sentence."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        return self._root(directory, runner, modules)

    def test_repeated_receiving_helper_keeps_distinct_text_actuals_4733(self):
        """Two calls to the same helper/list must retain both source-module operands."""
        with tempfile.TemporaryDirectory() as d:
            root = self._effect_contract_root_4733(
                d, "    parts = []\n    effects.fill(parts, one.TEXT)\n"
                   "    effects.fill(parts, text=two.TEXT)",
                "def fill(items, text):\n    items.append(text)\n")
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            for module in ("effect_source_one_4733", "effect_source_two_4733"):
                self.assertIn(module, derived)
                self.assertIn(("VOICE", 2), self._violations(
                    root, "src/data_sheets_schema/" + module + ".py", derived, spans))
            off, off_spans, _ = self._derive(root, sinks=False)
            for module in ("effect_source_one_4733", "effect_source_two_4733"):
                self.assertNotIn(module, off)
                self.assertNotIn(("VOICE", 2), self._violations(
                    root, "src/data_sheets_schema/" + module + ".py", off, off_spans))

    def test_projected_receiving_actual_refuses_instead_of_losing_text_4733(self):
        """The finite Name-actual effect contract cannot silently accept a projected list."""
        with tempfile.TemporaryDirectory() as d:
            root = self._effect_contract_root_4733(
                d, "    parts = [[]]\n    effects.fill(parts[0], one.TEXT)",
                "def fill(items, text):\n    items.append(text)\n")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect.*container"):
                self._derive(root)

    def test_recursive_receiving_helper_refuses_a_silent_partial_derivation_4733(self):
        """A recursive effect path must terminate analysis with an explicit refusal."""
        with tempfile.TemporaryDirectory() as d:
            root = self._effect_contract_root_4733(
                d, "    parts = []\n    effects.fill(parts, one.TEXT)",
                "def fill(items, text):\n    items.append(text)\n    fill(items, text)\n")
            with self.assertRaisesRegex(scan.ConfigError, "recursive receiving helper"):
                self._derive(root)

    def test_discarded_helper_extend_mapping_emits_inline_keys(self):
        """list.extend consumes mapping keys even without an explicit keys() call."""
        helper = ('ASIDE = "A VOICE aside this function never sends."\n\n'
                  'def add_policy(items):\n'
                  '    items.extend({"Neutral instruction sentence": None})\n')
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._discarded_container_effect_fixture(
                d, "    effects.add_policy(parts)", helper,
                "from data_sheets_schema import container_effect_4405 as effects\n")
            self.assertIn("container_effect_4405", derived)
            rel = "src/data_sheets_schema/container_effect_4405.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 1)})
            self.assertNotIn("hidden_policy_4405", derived)
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("container_effect_4405", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_discarded_helper_default_uses_definition_scope(self):
        """A callee-local shadow cannot change its already evaluated default."""
        helper = ('SYSTEM = "Describe the CHORUS cohort from its source records."\n'
                  'ASIDE = "A VOICE aside this function never sends."\n\n'
                  'def add_policy(items, text=SYSTEM):\n'
                  '    SYSTEM = "x"\n'
                  '    items.append(text)\n')
        with tempfile.TemporaryDirectory() as d:
            root, derived, spans = self._discarded_container_effect_fixture(
                d, "    effects.add_policy(parts)", helper,
                "from data_sheets_schema import container_effect_4405 as effects\n")
            self.assertIn("container_effect_4405", derived)
            rel = "src/data_sheets_schema/container_effect_4405.py"
            self.assertEqual(self._violations(root, rel, derived, spans),
                             {("CHORUS", 1), ("VOICE", 2)})
            self.assertNotIn("hidden_policy_4405", derived)
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("container_effect_4405", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_model_file_writer_is_a_seed_consumer_not_an_unknown_escape(self):
        """The real discovered model-file writer consumes the reached local text."""
        writer = ('from pathlib import Path\n'
                  'from data_sheets_schema import hidden_writer_policy_trace as policy\n\n'
                  'def emit(directory):\n'
                  '    parts = []\n'
                  '    parts.append(policy.SYSTEM)\n'
                  '    (Path(directory) / "neutral_healthsheet_only.txt").write_text("".join(parts))\n')
        modules = dict(PRECISION_MODULES)
        modules["model_writer_trace"] = writer
        modules["hidden_writer_policy_trace"] = (
            'SYSTEM = "Describe the CHORUS cohort from its source records."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, PRECISION_RUNNER, modules)
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["writers"], ["src/data_sheets_schema/model_writer_trace.py:7"])
            self.assertIn("_healthsheet_only.txt", facts["model_input_files"])
            self.assertIn("hidden_writer_policy_trace", derived)
            rel = "src/data_sheets_schema/hidden_writer_policy_trace.py"
            self.assertEqual(self._violations(root, rel, derived, spans),
                             {("CHORUS", 1), ("VOICE", 2)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("hidden_writer_policy_trace", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_unresolved_helper_receiving_model_container_refuses(self):
        """An actual unknown receiving call is not a terminal request consumer."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n", "from pathlib import Path\nfrom external_mutator import fill\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, "    parts = []\n    fill(parts)\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, dict(PRECISION_MODULES))
            parsed = _parsed(root, "src")
            index = scan._notes_index(root, parsed)
            sinks, facts = scan.model_input_sinks(root, parsed, index, [], set())
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            self.assertTrue(sinks)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("prompts_4085", off)

    def test_known_scalar_discarded_observer_keeps_text_flow_4733(self):
        """A literal string is not a mutable receiving container."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import scalar_observer_4733\n")
        runner = runner.replace("system=prompts_4085.SYSTEM", "system=scalar_observer_4733.render_scalar()")
        modules = dict(PRECISION_MODULES)
        modules["scalar_observer_4733"] = (
            'from external_observer import observe\n'
            'ASIDE = "A VOICE aside this module never sends."\n\n'
            'def render_scalar():\n'
            '    message = "Describe this neutral record from its source evidence."\n'
            '    observe(message)\n'
            '    return message\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, modules)
            derived, spans, _ = self._derive(root)
            self.assertIn("scalar_observer_4733", derived)
            rel = "src/data_sheets_schema/scalar_observer_4733.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("scalar_observer_4733", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_unknown_carrier_discarded_fill_does_not_gain_scalar_exemption_4733(self):
        """An unknown object cannot borrow the literal-string exemption."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom external_carrier import make_parts, fill\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, "    parts = make_parts()\n    fill(parts)\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "[parts]")
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, dict(PRECISION_MODULES))
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("prompts_4085", off)


    def test_incoming_formal_alias_cannot_be_proved_scalar_by_later_assignment_4733(self):
        """The alias still holds the caller's list after its formal is rebound."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import formal_alias_4733\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, "    parts = []\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "formal_alias_4733.render_parts(parts)")
        modules = dict(PRECISION_MODULES)
        modules["formal_alias_4733"] = (
            'from external_mutator import fill\n\n'
            'def render_parts(items):\n'
            '    alias = items\n'
            '    items = "x"\n'
            '    fill(alias)\n'
            '    return alias\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, modules)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("formal_alias_4733", off)

    def test_named_expression_rebinding_invalidates_scalar_effect_exemption(self):
        """A scalar name becomes the list passed to an unknown receiving call."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n", "from pathlib import Path\nfrom external_mutator import fill\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker,
                                '    parts = ""\n    (parts := [])\n    fill(parts)\n' + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, dict(PRECISION_MODULES))
            parsed = _parsed(root, "src")
            index = scan._notes_index(root, parsed)
            sinks, facts = scan.model_input_sinks(root, parsed, index, [], set())
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            self.assertTrue(sinks)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("prompts_4085", off)

    def test_with_target_rebinding_invalidates_scalar_effect_exemption(self):
        """The actual with-as value is a mutable list despite the earlier scalar."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom contextlib import nullcontext\nfrom external_mutator import fill\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker,
                                '    parts = ""\n    with nullcontext([]) as parts:\n        fill(parts)\n' + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, dict(PRECISION_MODULES))
            parsed = _parsed(root, "src")
            index = scan._notes_index(root, parsed)
            sinks, facts = scan.model_input_sinks(root, parsed, index, [], set())
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            self.assertTrue(sinks)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("prompts_4085", off)

    def _mapping_cycle_root_4733(self, directory, expression, *, outer_key="outer", inner_key="Neutral nested instruction sentence"):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nimport json\nfrom data_sheets_schema import cyclic_mapping_4733\n")
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", expression)
        modules = dict(PRECISION_MODULES)
        modules["cyclic_mapping_4733"] = (
            'ASIDE = "A VOICE aside this function never sends."\n\n'
            'def mapping():\n'
            f'    table = {{{outer_key!r}: {{"box": {{{inner_key!r}: None}}}}}}\n'
            f'    selected = table[{outer_key!r}]\n'
            '    table = selected\n'
            '    return table\n')
        return self._root(directory, runner, modules)

    def test_lookup_only_mapping_cycle_terminates_without_key_emission_4733(self):
        """A real finite reassignment creates a cycle in conservative local dataflow."""
        with tempfile.TemporaryDirectory() as d:
            root = self._mapping_cycle_root_4733(d, '[cyclic_mapping_4733.mapping()["box"]]')
            derived, spans, _ = self._derive(root)
            self.assertNotIn("cyclic_mapping_4733", derived)
            self.assertEqual(self._violations(root, "src/data_sheets_schema/cyclic_mapping_4733.py", derived, spans), set())

    def test_mapping_cycle_lookup_and_nested_key_emission_both_orders_4733(self):
        lookup = 'cyclic_mapping_4733.mapping()["box"]'
        emission = 'json.dumps(cyclic_mapping_4733.mapping()["box"])'
        for first, second in ((lookup, emission), (emission, lookup)):
            with self.subTest(first=first), tempfile.TemporaryDirectory() as d:
                root = self._mapping_cycle_root_4733(d, '[' + first + ', ' + second + ']')
                derived, spans, _ = self._derive(root)
                self.assertIn("cyclic_mapping_4733", derived)
                rel = "src/data_sheets_schema/cyclic_mapping_4733.py"
                self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 1)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("cyclic_mapping_4733", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_mapping_cycle_selected_serialization_does_not_emit_outer_key_4733(self):
        """Termination must not widen a selected inner mapping to every outer key."""
        with tempfile.TemporaryDirectory() as d:
            root = self._mapping_cycle_root_4733(
                d, '[json.dumps(cyclic_mapping_4733.mapping()["box"])]',
                outer_key="Neutral outer selector sentence", inner_key="id")
            derived, spans, _ = self._derive(root)
            self.assertNotIn("cyclic_mapping_4733", derived)
            self.assertEqual(self._violations(root, "src/data_sheets_schema/cyclic_mapping_4733.py", derived, spans), set())

    def _builtin_copy_root_4733(self, directory, statements, *, extra_import=""):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from data_sheets_schema import copied_text_4733 as copied_text\n" + extra_import)
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, statements + "\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "[cached, parts]")
        modules = dict(PRECISION_MODULES)
        modules["copied_text_4733"] = (
            'TEXT = "Describe this neutral record from the captured evidence."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        return self._root(directory, runner, modules)

    def test_builtin_shallow_copy_outer_append_retains_emitted_text_4733(self):
        """Both real request operands remain reached; only the copied outer list gains text."""
        with tempfile.TemporaryDirectory() as d:
            root = self._builtin_copy_root_4733(
                d, "    cached = []\n    parts = list(cached)\n    parts.append(copied_text.TEXT)")
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            self.assertIn("copied_text_4733", derived)
            rel = "src/data_sheets_schema/copied_text_4733.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("copied_text_4733", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_shadowed_or_custom_copy_does_not_gain_builtin_receiver_admission_4733(self):
        """A constructor spelling alone does not prove a builtin shallow list copy."""
        for imported, factory in (("from external_copies import list\n", "list"),
                                  ("from external_copies import make_copy\n", "make_copy")):
            with self.subTest(factory=factory), tempfile.TemporaryDirectory() as d:
                root = self._builtin_copy_root_4733(
                    d, "    cached = []\n    parts = " + factory + "(cached)\n"
                       "    parts.append(copied_text.TEXT)", extra_import=imported)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("copied_text_4733", off)

    def test_shallow_copy_shared_nested_mutation_remains_explicitly_unsupported_4733(self):
        """The shallow copy shares its inner list; the outer-copy allowance cannot certify that edge."""
        with tempfile.TemporaryDirectory() as d:
            root = self._builtin_copy_root_4733(
                d, "    cached = [[]]\n    parts = list(cached)\n"
                   "    parts[0].append(copied_text.TEXT)")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("copied_text_4733", off)

    def _computed_argument_root_4733(self, directory, operation, *, initial="[computed_text.TEXT]"):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from external_observer import observe, fill\n"
            "from data_sheets_schema import computed_text_4733 as computed_text\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, "    parts = " + initial + "\n" + operation + "\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        modules = dict(PRECISION_MODULES)
        modules["computed_text_4733"] = (
            'TEXT = "Describe this neutral record using the captured evidence."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        return self._root(directory, runner, modules)

    def test_computed_boolean_and_formatted_string_are_not_container_actuals_4733(self):
        """The unknown observer gets a bool or string, not the list object used to form it."""
        for operation in ("    observe(not parts)", "    observe(f'{parts}')"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as d:
                root = self._computed_argument_root_4733(d, operation)
                derived, spans, facts = self._derive(root)
                self.assertEqual(facts["request"]["class"], "PhaseRequest")
                self.assertEqual(len(facts["requests"]), 1)
                self.assertIn("computed_text_4733", derived)
                rel = "src/data_sheets_schema/computed_text_4733.py"
                self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("computed_text_4733", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_builtin_predicate_generator_does_not_escape_emitted_container_4733(self):
        """An unshadowed builtin consumes a generator of identity-test booleans."""
        with tempfile.TemporaryDirectory() as d:
            root = self._computed_argument_root_4733(d, "    any(item is None for item in parts)")
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertIn("computed_text_4733", derived)
            rel = "src/data_sheets_schema/computed_text_4733.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("computed_text_4733", off)

    def test_computed_argument_fix_does_not_hide_nested_container_escape_4733(self):
        """This projected argument can be the same inner mutable list sent in the request."""
        with tempfile.TemporaryDirectory() as d:
            root = self._computed_argument_root_4733(d, "    fill(parts[0])", initial="[[]]")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_generator_yielding_shared_mutable_elements_remains_unsupported_4733(self):
        """Unlike a builtin boolean predicate, an unknown consumer can mutate yielded elements."""
        with tempfile.TemporaryDirectory() as d:
            root = self._computed_argument_root_4733(
                d, "    observe(item for item in parts)", initial="[[]]")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)

    def _predicate_boundary_root_4733(self, directory, statements, *, content="parts", extra_import="", prefix=""):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from external_mutator import fill, observe\n"
            "from data_sheets_schema import predicate_text_4733 as predicate_text\n" + extra_import)
        if prefix:
            runner = prefix + runner
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, statements + "\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", content)
        modules = dict(PRECISION_MODULES)
        modules["predicate_text_4733"] = (
            'TEXT = "Describe this neutral record using captured evidence."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        return self._root(directory, runner, modules)

    def test_real_path_exists_generator_preserves_model_text_discovery_4733(self):
        """The real launcher shape constructs Paths from selected output strings."""
        with tempfile.TemporaryDirectory() as d:
            root = self._predicate_boundary_root_4733(
                d, '    job = {"output_directories": [predicate_text.TEXT]}\n'
                   '    if any(Path(p).exists() for p in job["output_directories"]):\n'
                   '        raise ValueError("output already exists")', content="job")
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertIn("predicate_text_4733", derived)
            rel = "src/data_sheets_schema/predicate_text_4733.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("predicate_text_4733", off)

    def test_shadowed_predicate_consumers_do_not_gain_builtin_admission_4733(self):
        """A same-spelled imported consumer may mutate each yielded inner list."""
        for name in ("any", "all"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = self._predicate_boundary_root_4733(
                    d, "    parts = [[]]\n    " + name + "(item for item in parts)",
                    extra_import="from external_predicates import " + name + "\n")
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                self._derive(root, sinks=False)

    def test_rebound_path_cannot_hide_generator_element_escape_4733(self):
        """A replacement Path factory receives the same mutable element, even before .exists()."""
        with tempfile.TemporaryDirectory() as d:
            root = self._predicate_boundary_root_4733(
                d, '    job = {"output_directories": [[]]}\n'
                   '    any(Path(p).exists() for p in job["output_directories"])', content="job",
                extra_import="from external_paths import make_path\nPath = make_path\n")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_nested_mutation_is_not_hidden_by_scalar_actual_result_4733(self):
        """Removing an outer scalar receiving edge must retain its nested unknown mutator."""
        for expression in ("not fill(parts)", "f'{fill(parts)}'"):
            with self.subTest(expression=expression), tempfile.TemporaryDirectory() as d:
                root = self._predicate_boundary_root_4733(
                    d, "    parts = []\n    observe(" + expression + ")")
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                self._derive(root, sinks=False)

    def test_generator_bound_mutable_element_is_traced_into_nested_call_4733(self):
        """The yielded result is bool, but fill still receives a shared inner list."""
        with tempfile.TemporaryDirectory() as d:
            root = self._predicate_boundary_root_4733(
                d, "    parts = [[]]\n    any(fill(item) is None for item in parts)")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_generator_target_shadow_does_not_alias_outer_emitted_list_4733(self):
        """The generator's parts binding is local to that comprehension and yields bools."""
        with tempfile.TemporaryDirectory() as d:
            root = self._predicate_boundary_root_4733(
                d, "    parts = [predicate_text.TEXT]\n    any(parts is None for parts in [None])")
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertIn("predicate_text_4733", derived)
            rel = "src/data_sheets_schema/predicate_text_4733.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("predicate_text_4733", off)

    def test_predicate_generator_target_mutation_cannot_silently_lose_emitted_text_4733(self):
        """A scalar yielded value does not make the generator's target assignment harmless."""
        cases = (
            ("subscript", "    parts = [None]", "parts[0]", "parts[0]", ""),
            ("attribute", "    parts = SimpleNamespace(text=None)", "parts.text", "parts.text",
             "from types import SimpleNamespace\n"),
        )
        for label, initial, target, content, imported in cases:
            with self.subTest(target=label), tempfile.TemporaryDirectory() as d:
                root = self._predicate_boundary_root_4733(
                    d, initial + "\n    any(False for " + target + " in [predicate_text.TEXT])",
                    content=content, extra_import=imported)
                # These stores are outside the finite direct-Name target model.
                # The emitted TEXT must not disappear under a scalar-elt exemption.
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("predicate_text_4733", off)

    def test_predicate_generator_target_store_either_refuses_or_retains_real_text_4733(self):
        """A returned derivation must include the module whose string is stored and emitted."""
        cases = (
            ("subscript", "    parts = [None]", "parts[0]", "parts[0]", ""),
            ("attribute", "    parts = SimpleNamespace(text=None)", "parts.text", "parts.text",
             "from types import SimpleNamespace\n"),
        )
        for label, initial, target, content, imported in cases:
            with self.subTest(target=label), tempfile.TemporaryDirectory() as d:
                root = self._predicate_boundary_root_4733(
                    d, initial + "\n    any(False for " + target + " in [predicate_text.TEXT])",
                    content=content, extra_import=imported)
                try:
                    derived, spans, facts = self._derive(root)
                except scan.ConfigError:
                    # Explicit refusal is permitted for this unsupported store.
                    # A returned partial derivation is not.
                    continue
                self.assertEqual(facts["request"]["class"], "PhaseRequest")
                self.assertEqual(len(facts["requests"]), 1)
                self.assertIn("predicate_text_4733", derived)
                rel = "src/data_sheets_schema/predicate_text_4733.py"
                self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("predicate_text_4733", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_assigned_scalar_results_do_not_alias_their_container_inputs_4733(self):
        """Assigning a fresh string or bool does not retain a mutable reference to parts."""
        for assignment in ("message = f'{parts}'", "message = not parts"):
            with self.subTest(assignment=assignment), tempfile.TemporaryDirectory() as d:
                root = self._predicate_boundary_root_4733(
                    d, "    parts = [predicate_text.TEXT]\n    " + assignment + "\n    observe(message)")
                derived, spans, facts = self._derive(root)
                self.assertEqual(facts["request"]["class"], "PhaseRequest")
                self.assertIn("predicate_text_4733", derived)
                rel = "src/data_sheets_schema/predicate_text_4733.py"
                self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 2)})
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("predicate_text_4733", off)

    def test_known_identity_result_retains_unsupported_receiving_escape_4733(self):
        """A consumed known helper can return the original list, unlike a fresh scalar expression."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom external_mutator import fill\n"
            "from data_sheets_schema import identity_alias_4733\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(
            marker, "    parts = []\n    alias = identity_alias_4733.identity(parts)\n"
                    "    fill(alias)\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "parts")
        modules = dict(PRECISION_MODULES)
        modules["identity_alias_4733"] = "def identity(value):\n    return value\n"
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d, runner, modules)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_assigned_formatted_scalar_keeps_its_nested_mutator_check_4733(self):
        """The assigned result is a string, but its inner call still receives the emitted list."""
        with tempfile.TemporaryDirectory() as d:
            root = self._predicate_boundary_root_4733(
                d, "    parts = []\n    message = f'{fill(parts)}'\n    observe(message)")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)


    def test_local_text_helper_imports_ignore_disjoint_function_bindings_4588(self):
        for library, helper in (("json", "dumps"), ("yaml", "safe_dump"), ("textwrap", "dedent")):
            with self.subTest(library=library), tempfile.TemporaryDirectory() as directory:
                imported = "from " + library + " import " + helper + " as render"
                source = ("def content():\n    " + imported +
                          '\n    return render("Neutral instruction sentence")\n'
                          "\ndef unrelated():\n    " + imported + '\n    return render("unused")\n')
                root, derived, spans = self._text_helper_alias_fixture_4733(directory, source)
                self.assertIn("aliased_text_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("aliased_text_4405", off)

    def test_module_text_helper_import_ignores_disjoint_local_shadows_4588(self):
        """Bindings in unexecuted sibling scopes must not hide a module-level text helper."""
        for shadow in (
            "class Unrelated:\n    render = None\n    def method(self):\n"
            "        from json import dumps as render\n        return render('unused')\n",
            "def unrelated(render=None):\n    return render\n",
        ):
            with self.subTest(shadow=shadow), tempfile.TemporaryDirectory() as directory:
                source = ('from json import dumps as render\n\ndef content():\n'
                          '    return render("Neutral instruction sentence")\n\n' + shadow)
                root, derived, spans = self._text_helper_alias_fixture_4733(directory, source)
                self.assertIn("aliased_text_4405", derived)
                self.assertIn(("VOICE", 1), self._violations(
                    root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("aliased_text_4405", off)

    def test_text_helper_scope_resolution_keeps_actual_rebinding_conservative_4588(self):
        """Actual rebinding in the active scope must decline text-helper promotion."""
        prefix = "from json import dumps as render\n\n"
        cases = {
            "local_assignment": ('def content():\n    from json import dumps as render\n'
                                 '    render = lambda value: ""\n'
                                 '    return render("Neutral instruction sentence")\n'),
            "parameter_shadow": ('def content(render=lambda value: ""):\n'
                                 '    return render("Neutral instruction sentence")\n'),
            "module_rebinding": ('render = lambda value: ""\n'
                                 'def content():\n'
                                 '    return render("Neutral instruction sentence")\n'),
            "del_rebinding": ('def content():\n    from json import dumps as render\n'
                              '    del render\n'
                              '    render = lambda value: ""\n'
                              '    return render("Neutral instruction sentence")\n'),
        }
        for label, body in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as directory:
                root, derived, spans = self._text_helper_alias_fixture_4733(directory, prefix + body)
                self.assertNotIn("aliased_text_4405", derived)
                self.assertEqual(set(), self._violations(
                    root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))


    def _consumed_helper_root_4733(self, directory, invocation, helper, imports=""):
        """Both the helper's scalar return and its populated list reach a real request."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from data_sheets_schema import consumed_helper_4733 as effects\n" + imports)
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, "    parts = []\n" + invocation + "\n" + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "[selected, parts]")
        modules = dict(PRECISION_MODULES)
        modules["consumed_helper_4733"] = helper
        modules["consumed_policy_4733"] = (
            'SYSTEM = "Describe the CHORUS cohort from its source records."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        return self._root(directory, runner, modules)

    def _assert_consumed_policy_4733(self, root, derived, spans, facts):
        self.assertEqual(facts["request"]["class"], "PhaseRequest")
        self.assertEqual(len(facts["requests"]), 1)
        self.assertIn("consumed_policy_4733", derived)
        rel = "src/data_sheets_schema/consumed_policy_4733.py"
        self.assertEqual(self._violations(root, rel, derived, spans),
                         {("CHORUS", 1), ("VOICE", 2)})
        off, off_spans, _ = self._derive(root, sinks=False)
        self.assertNotIn("consumed_policy_4733", off)
        self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_consumed_helper_return_keeps_its_helper_owned_container_text_4733(self):
        """Consuming a scalar return cannot discard the helper's modeled append."""
        helper = (
            'from data_sheets_schema import consumed_policy_4733 as policy\n\n'
            'def fill(items):\n'
            '    items.append(policy.SYSTEM)\n'
            '    return "selected.txt"\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._consumed_helper_root_4733(
                d, "    selected = effects.fill(parts)", helper)
            derived, spans, facts = self._derive(root)
            self._assert_consumed_policy_4733(root, derived, spans, facts)

    def test_consumed_helper_explicit_imported_argument_is_a_masking_control_4733(self):
        """Historical data-argument traversal already preserves this imported constant."""
        helper = ('def fill(items, text):\n'
                  '    items.append(text)\n'
                  '    return "selected.txt"\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._consumed_helper_root_4733(
                d, "    selected = effects.fill(parts, policy.SYSTEM)", helper,
                "from data_sheets_schema import consumed_policy_4733 as policy\n")
            derived, spans, facts = self._derive(root)
            self._assert_consumed_policy_4733(root, derived, spans, facts)

    def test_consumed_projected_receiver_either_refuses_or_keeps_real_text_4733(self):
        """An unmodeled receiver retains a list and mutates it before the request."""
        helper = (
            'from data_sheets_schema import consumed_policy_4733 as policy\n\n'
            'class Holder:\n'
            '    def __init__(self, items):\n'
            '        self.items = items\n'
            '    def fill(self):\n'
            '        self.items.append(policy.SYSTEM)\n'
            '        return "selected.txt"\n\n'
            'def make(items):\n'
            '    return Holder(items)\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._consumed_helper_root_4733(
                d, "    selected = effects.make(parts).fill()", helper)
            try:
                derived, spans, facts = self._derive(root)
            except scan.ConfigError as error:
                self.assertIn("unsupported effect", str(error))
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("consumed_policy_4733", off)
            else:
                self._assert_consumed_policy_4733(root, derived, spans, facts)


    def _local_receiver_observer_fixture_trace(self, directory, initialization, operation,
                                               payload="parts", extra_source="", extra_import=""):
        """The hidden sentence occurs only as this operation's operand/default."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from data_sheets_schema import observer_operand_trace as hidden\n" + extra_import)
        if extra_source:
            runner += "\n" + extra_source
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(marker, initialization + operation + marker)
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", payload)
        modules = dict(PRECISION_MODULES)
        modules["observer_operand_trace"] = (
            'TEXT = "Describe the CHORUS cohort from its source records."\n'
            'ASIDE = "A VOICE aside this module never sends."\n')
        root = self._root(directory, runner, modules)
        parsed = _parsed(root, "src")
        index = scan._notes_index(root, parsed)
        sinks, facts = scan.model_input_sinks(root, parsed, index, [], set())
        self.assertTrue(sinks)
        self.assertTrue(facts["requests"])
        off, off_spans, _ = self._derive(root, sinks=False)
        self.assertNotIn("observer_operand_trace", off)
        self.assertEqual(
            self._violations(root, "src/data_sheets_schema/observer_operand_trace.py", off, off_spans),
            set(),
        )
        return root
    def test_discarded_builtin_observer_operands_do_not_become_emitted_text_trace(self):
        """Primitive count/index/get operands do not enter the returned container."""
        cases = (
            ("list_count", '    parts = ["Neutral instruction."]\n',
             "    parts.count(hidden.TEXT)\n", "parts"),
            ("list_index", '    parts = ["Neutral instruction."]\n',
             "    try:\n        parts.index(hidden.TEXT)\n    except ValueError:\n        pass\n", "parts"),
            ("dict_get_key", '    parts = {"neutral": "Neutral instruction."}\n',
             "    parts.get(hidden.TEXT)\n", "list(parts.values())"),
            ("dict_get_default", '    parts = {"neutral": "Neutral instruction."}\n',
             '    parts.get("missing", hidden.TEXT)\n', "list(parts.values())"),
        )
        for label, initialization, operation, payload in cases:
            with self.subTest(observer=label), tempfile.TemporaryDirectory() as directory:
                root = self._local_receiver_observer_fixture_trace(
                    directory, initialization, operation, payload)
                derived, spans, _ = self._derive(root)
                self.assertIn("prompts_4085", derived)
                self.assertNotIn("observer_operand_trace", derived)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/observer_operand_trace.py", derived, spans), set())

    def test_local_observer_correction_preserves_append_and_emitted_default_trace(self):
        """A real mutation or used get-default still contributes the hidden sentence."""
        cases = (
            ("append", "    parts = []\n", "    parts.append(hidden.TEXT)\n", "parts"),
            ("used_get_default", "    parts = {}\n", "", '[parts.get("missing", hidden.TEXT)]'),
        )
        for label, initialization, operation, payload in cases:
            with self.subTest(emission=label), tempfile.TemporaryDirectory() as directory:
                root = self._local_receiver_observer_fixture_trace(
                    directory, initialization, operation, payload)
                derived, spans, _ = self._derive(root)
                self.assertIn("observer_operand_trace", derived)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/observer_operand_trace.py", derived, spans),
                    {("CHORUS", 1), ("VOICE", 2)})

    def test_custom_or_unknown_observer_spelling_never_silently_hides_text_trace(self):
        """A count spelling does not certify a custom/unknown receiver as read-only."""
        cases = (
            ("custom_list_subclass", "    parts = CapturingListTrace()\n", "",
             "class CapturingListTrace(list):\n"
             "    def count(self, text):\n"
             "        self.append(text)\n"
             "        return 0\n"),
            ("unknown_factory", "    parts = make_parts()\n",
             "from external_receiver_factory_trace import make_parts\n", ""),
        )
        for label, initialization, extra_import, extra_source in cases:
            with self.subTest(receiver=label), tempfile.TemporaryDirectory() as directory:
                root = self._local_receiver_observer_fixture_trace(
                    directory, initialization, "    parts.count(hidden.TEXT)\n",
                    extra_source=extra_source, extra_import=extra_import)
                try:
                    derived, spans, _ = self._derive(root)
                except scan.ConfigError as exc:
                    self.assertIn("unsupported effect", str(exc))
                else:
                    # Either explicit unsupported-effect refusal or conservative
                    self.assertIn("observer_operand_trace", derived)
                    self.assertEqual(
                        self._violations(root, "src/data_sheets_schema/observer_operand_trace.py", derived, spans),
                        {("CHORUS", 1), ("VOICE", 2)},
                    )

    def test_direct_local_text_helper_import_overrides_same_named_module_reader_4588(self):
        with tempfile.TemporaryDirectory() as directory:
            source = ('from pathlib import Path as render\n\n'
                      'def content():\n'
                      '    from json import dumps as render\n'
                      '    return render("Neutral instruction sentence")\n')
            root, derived, spans = self._text_helper_alias_fixture_4733(directory, source)
            self.assertIn("aliased_text_4405", derived)
            self.assertIn(("VOICE", 1), self._violations(
                root, "src/data_sheets_schema/aliased_text_4405.py", derived, spans))
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("aliased_text_4405", off)
            self.assertEqual(set(), self._violations(root, "src/data_sheets_schema/aliased_text_4405.py", off, spans))

    def test_literal_mapping_get_chain_keeps_consumed_text_4733(self):
        """Literal returned mapping lookups still carry the selected model text."""
        with tempfile.TemporaryDirectory() as d:
            root = self._consumed_helper_root_4733(
                d, '    selected = {"row": {"text": policy.SYSTEM}}.get("row").get("text")', "",
                "from data_sheets_schema import consumed_policy_4733 as policy\n")
            derived, spans, facts = self._derive(root)
            self._assert_consumed_policy_4733(root, derived, spans, facts)


    def test_builtin_mapping_view_list_copy_retains_emission_projection_trace(self):
        """Only key/items copies emit an inline key; values copy stays values-only."""
        for view in ("keys", "items", "values"):
            with self.subTest(view=view), tempfile.TemporaryDirectory() as directory:
                body = ('    mapping = {"Neutral instruction sentence": 1}\n'
                        '    return list(mapping.' + view + '())')
                root = self._inline_key_context_fixture(directory, body)
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertIn("prompts_4085", derived)
                if view in {"keys", "items"}:
                    self.assertIn("key_context_trace", derived)
                    self.assertEqual(self._violations(
                        root, "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
                else:
                    self.assertNotIn("key_context_trace", derived)
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_context_trace", off)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/key_context_trace.py", off, off_spans), set())

    def test_mapping_view_copy_requires_actual_builtin_container_and_list_trace(self):
        """Unknown/custom mapping methods and shadowed list cannot gain purity."""
        cases = (
            ("unknown_mapping", '    from external_mapping_source_trace import make_mapping\n'
             '    mapping = make_mapping()\n    return list(mapping.values())'),
            ("custom_dict_subclass", '    class Custom(dict):\n'
             '        def values(self):\n            return ["Custom instruction sentence"]\n'
             '    mapping = Custom()\n    return list(mapping.values())'),
            ("shadowed_list", '    list = spec.builder\n'
             '    mapping = {"Neutral instruction sentence": 1}\n'
             '    return list(mapping.values())'),
        )
        for label, body in cases:
            with self.subTest(boundary=label), tempfile.TemporaryDirectory() as directory:
                root = self._inline_key_context_fixture(directory, body)
                parsed = _parsed(root, "src")
                index = scan._notes_index(root, parsed)
                sinks, facts = scan.model_input_sinks(root, parsed, index, [], set())
                self.assertTrue(sinks)
                self.assertTrue(facts["requests"])
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_context_trace", off)


    def test_proved_list_augmentation_keeps_helper_owned_emitted_text_4733(self):
        """The supported in-place list update follows text owned only by its helper."""
        helper = (
            'from data_sheets_schema import consumed_policy_4733 as policy\n\n'
            'def fill(items):\n'
            '    items += [policy.SYSTEM]\n'
            '    return "selected.txt"\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._consumed_helper_root_4733(
                d, "    selected = effects.fill(parts)", helper)
            derived, spans, facts = self._derive(root)
            self._assert_consumed_policy_4733(root, derived, spans, facts)

    def test_list_augmentation_keeps_nested_unknown_receiving_call_refusal_4733(self):
        """A literal RHS list does not make a nested mutating callback safe."""
        helper = ('from external_mutator import mutate\n\n'
                  'def fill(items):\n'
                  '    items += [mutate(items)]\n'
                  '    return "selected.txt"\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._consumed_helper_root_4733(
                d, "    selected = effects.fill(parts)", helper)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("consumed_policy_4733", off)

    def test_literal_join_contract_does_not_certify_custom_receivers_or_iterables_4733(self):
        cases = (
            ("custom_receiver", "    selected = joiner.join(parts)",
             "from external_joiner import joiner\n"),
            ("custom_iterable", '    parts = make_parts()\n    selected = "".join(parts)',
             "from external_iterable import make_parts\n"),
        )
        for label, invocation, imports in cases:
            with self.subTest(boundary=label), tempfile.TemporaryDirectory() as d:
                root = self._consumed_helper_root_4733(d, invocation, "", imports)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("consumed_policy_4733", off)


    def _address_adapter_root_4588(self, directory, adapter, *, content=None):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from data_sheets_schema import address_adapter_4588 as addresses\n")
        runner = runner.replace("[guide, value, ids_4085.label(spec)]",
                                'addresses.content("source.txt")')
        modules = dict(PRECISION_MODULES)
        modules["address_adapter_4588"] = (
            'from pathlib import Path\n'
            'ASIDE = "A VOICE aside the address adapter never sends."\n\n'
            + adapter + '\n' + (content or
                'def content(record_path):\n'
                '    record_path = select_address(record_path)\n'
                '    return f"Use the neutral record at {record_path}."\n'))
        return self._root(directory, runner, modules)

    def test_closed_path_address_adapter_keeps_real_text_derivation_4588(self):
        """A conditional address adapter has no receiving mutation or escape."""
        adapter = ('def select_address(record_path):\n'
                   '    path = record_path if record_path is not None else Path("source.txt")\n'
                   '    if path is None:\n'
                   '        raise FileNotFoundError("no selected address")\n'
                   '    return Path(path)\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._address_adapter_root_4588(directory, adapter)
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            self.assertIn("address_adapter_4588", derived)
            rel = "src/data_sheets_schema/address_adapter_4588.py"
            self.assertIn(("VOICE", 2), self._violations(root, rel, derived, spans))
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("address_adapter_4588", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_path_adapter_does_not_hide_unknown_or_rebound_receiving_calls_4588(self):
        adapters = (
            'from external_mutator import fill\n'
            'def select_address(record_path):\n'
            '    fill(record_path)\n'
            '    return Path(record_path)\n',
            'from external_mutator import fill\n'
            'def select_address(record_path):\n'
            '    return Path(fill(record_path))\n',
            'from external_mutator import Path\n'
            'def select_address(record_path):\n'
            '    return Path(record_path)\n',
            'def select_address(record_path):\n'
            '    selected = Path(record_path)\n'
            '    from external_mutator import carrier as selected\n'
            '    return selected\n',
        )
        for adapter in adapters:
            with self.subTest(adapter=adapter), tempfile.TemporaryDirectory() as directory:
                root = self._address_adapter_root_4588(directory, adapter)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("address_adapter_4588", off)

    def test_detached_path_result_does_not_erase_an_earlier_incoming_alias_4588(self):
        """Only the converted result is detached; an earlier alias retains its input."""
        adapter = ('from external_mutator import fill\n'
                   'def select_address(record_path):\n'
                   '    return Path(record_path)\n')
        content = ('def content(record_path):\n'
                   '    previous = record_path\n'
                   '    record_path = select_address(record_path)\n'
                   '    fill(previous)\n'
                   '    return [f"Use the neutral record at {record_path}.", previous]\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._address_adapter_root_4588(directory, adapter, content=content)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("address_adapter_4588", off)

    def test_closed_address_proof_rejects_implicit_incoming_callbacks_4588(self):
        """Address conversion cannot hide earlier invocation/formatting/unpacking."""
        operations = ("record_path()", 'f"{record_path}"', "[*record_path]",
                      "{record_path: None}")
        carrier = ('class Address:\n'
                   '    def __fspath__(self):\n        return "source.txt"\n'
                   '    def __call__(self):\n        self.touched = True\n'
                   '    def __format__(self, spec):\n'
                   '        self.touched = True\n        return "source.txt"\n'
                   '    def __iter__(self):\n'
                   '        self.touched = True\n        return iter(())\n'
                   '    def __hash__(self):\n'
                   '        self.touched = True\n        return 1\n\n')
        for operation in operations:
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                adapter = carrier + ('def select_address(record_path):\n'
                                     '    ' + operation + '\n'
                                     '    return Path(record_path)\n')
                root = self._address_adapter_root_4588(directory, adapter)
                runner = root / "src/data_sheets_schema/api_runner.py"
                original = runner.read_text(encoding="utf-8")
                self.assertEqual(original.count('addresses.content("source.txt")'), 1)
                runner.write_text(original.replace('addresses.content("source.txt")',
                                                   'addresses.content(addresses.Address())'), encoding="utf-8")
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("address_adapter_4588", off)


    def test_primitive_caller_values_support_closed_local_representations_4733(self):
        """Both import spellings carry real literal text through a list representation."""
        helper = ('def describe(value):\n'
                  '    items = []\n    alias = items\n    alias.append(value)\n'
                  '    return str(items)\n')
        for actual, imports in (
            ('policy.SYSTEM', 'from data_sheets_schema import consumed_policy_4733 as policy\n'),
            ('SYSTEM', 'from data_sheets_schema.consumed_policy_4733 import SYSTEM\n'),
        ):
            with self.subTest(actual=actual), tempfile.TemporaryDirectory() as directory:
                root = self._consumed_helper_root_4733(
                    directory, '    selected = effects.describe(' + actual + ')', helper, imports)
                derived, spans, facts = self._derive(root)
                self._assert_consumed_policy_4733(root, derived, spans, facts)

    def test_primitive_repr_facts_do_not_leak_between_callers_4733(self):
        """A real custom repr remains unsupported beside a safe caller, in both orders."""
        helper = ('from data_sheets_schema import consumed_policy_4733 as policy\n\n'
                  'class Custom:\n    def __repr__(self):\n        return policy.SYSTEM\n\n'
                  'def describe(value):\n    items = [value]\n    return str(items)\n')
        calls = ['effects.describe("ordinary text")', 'effects.describe(effects.Custom())']
        for unsafe_first in (False, True):
            with self.subTest(unsafe_first=unsafe_first), tempfile.TemporaryDirectory() as directory:
                ordered = list(reversed(calls)) if unsafe_first else calls
                root = self._consumed_helper_root_4733(
                    directory, '    selected = (' + ', '.join(ordered) + ')', helper)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                self._derive(root, sinks=False)

    def test_primitive_repr_proof_keeps_nested_custom_callbacks_4733(self):
        """A primitive actual does not prove a separately nested custom element harmless."""
        helper = ('from data_sheets_schema import consumed_policy_4733 as policy\n\n'
                  'class Custom:\n    def __repr__(self):\n        return policy.SYSTEM\n\n'
                  'def describe(value):\n    items = [value, [Custom()]]\n'
                  '    return str(items)\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(
                directory, '    selected = effects.describe("ordinary text")', helper)
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_primitive_repr_does_not_ignore_prior_receiving_helper_mutation_4733(self):
        """A fresh literal may gain callback-bearing elements through a resolved helper."""
        helper = ('from data_sheets_schema import consumed_policy_4733 as policy\n\n'
                  'class Custom:\n    def __repr__(self):\n        return policy.SYSTEM\n\n'
                  'def fill(items):\n    items.append(Custom())\n\n'
                  'def describe(value):\n    items = []\n    fill(items)\n'
                  '    items.append(value)\n    return str(items)\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(
                directory, '    selected = effects.describe("ordinary text")', helper)
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_shadowed_str_keeps_its_real_receiving_effect_4733(self):
        """The spelling str cannot suppress a resolved helper's source-owned append."""
        helper = ('from data_sheets_schema import consumed_policy_4733 as policy\n\n'
                  'def str(items):\n    items.append(policy.SYSTEM)\n    return items\n\n'
                  'def describe(value):\n    items = [value]\n    return str(items)\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(
                directory, '    selected = effects.describe("ordinary text")', helper)
            try:
                derived, spans, facts = self._derive(root)
            except scan.ConfigError:
                return  # An explicit bounded refusal is also truthful here.
            self._assert_consumed_policy_4733(root, derived, spans, facts)


    def test_authenticated_json_summary_keeps_mapping_text_trace(self):
        """Direct external module/name imports retain the established JSON flow."""
        variants = (
            ("module", "", "json.dumps"),
            ("name_alias", "    from json import dumps as encode\n", "encode"),
            ("module_alias", "    import json as standard_json\n", "standard_json.dumps"),
        )
        for label, imports, callee in variants:
            with self.subTest(route=label), tempfile.TemporaryDirectory() as d:
                body = (imports + '    mapping = {"Neutral instruction sentence": spec.value}\n'
                        '    return ' + callee + '(mapping)')
                root = self._inline_key_context_fixture(d, body)
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertIn("key_context_trace", derived)
                self.assertEqual(self._violations(root,
                    "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_context_trace", off)
                self.assertEqual(self._violations(root,
                    "src/data_sheets_schema/key_context_trace.py", off, off_spans), set())

    def test_json_summary_rejects_replaced_identity_and_explicit_callback_trace(self):
        """A dumps spelling or explicit callback never gets external summary authority."""
        helper = ('from data_sheets_schema import json_policy_trace as policy\n\n'
                  'def dumps(mapping):\n'
                  '    mapping["late"] = policy.TEXT\n'
                  '    return ""\n\n'
                  'def convert(value):\n'
                  '    return policy.TEXT\n')
        cases = (
            ("local_helper", '    return key_factory_trace.dumps(mapping)', None),
            ("rebound_module_attribute", '    json.dumps = key_factory_trace.dumps\n'
             '    return json.dumps(mapping)', None),
            ("represented_json_module", '    return json.dumps(mapping)', helper),
            ("explicit_default_callback", '    return json.dumps(mapping, default=key_factory_trace.convert)', None),
        )
        for label, ending, local_json in cases:
            with self.subTest(route=label), tempfile.TemporaryDirectory() as d:
                root = self._inline_key_context_fixture(d,
                    '    mapping = {"neutral": object()}\n' + ending,
                    {"key_factory_trace": helper,
                     "json_policy_trace": 'TEXT = "Describe the CHORUS cohort."\n'})
                if local_json is not None:
                    _write(root / "src/json.py", local_json)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("json_policy_trace", off)

    def test_json_summary_does_not_skip_separate_receiving_calls_trace(self):
        """Consumed serialization does not waive a preceding known/unknown mutation."""
        helper = ('from data_sheets_schema import json_policy_trace as policy\n\n'
                  'def mutate(mapping):\n'
                  '    mapping["late"] = policy.TEXT\n')
        for label, statement in (
                ("resolved_mutation", "    key_factory_trace.mutate(mapping)"),
                ("unknown_receiving_call", "    from external_mutator import fill\n    fill(mapping)")):
            with self.subTest(route=label), tempfile.TemporaryDirectory() as d:
                root = self._inline_key_context_fixture(d,
                    '    mapping = {"Neutral instruction sentence": spec.value}\n'
                    + statement + '\n    return json.dumps(mapping)',
                    {"key_factory_trace": helper,
                     "json_policy_trace": 'TEXT = "Describe the CHORUS cohort."\n'})
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("json_policy_trace", off)


    def test_entry_address_conversion_dominates_later_readonly_use_4588(self):
        """A converted formal is a detached Path before its next receiving use."""
        adapter = ('def select_address(value):\n    return Path(value)\n\n'
                   'def inspect_address(value):\n    return value.is_absolute()\n')
        content = ('def content(record_path):\n'
                   '    record_path = select_address(record_path)\n'
                   '    inspect_address(record_path)\n'
                   '    return f"Use the neutral record at {record_path}."\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._address_adapter_root_4588(directory, adapter, content=content)
            derived, spans, facts = self._derive(root)
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertEqual(len(facts["requests"]), 1)
            self.assertIn("address_adapter_4588", derived)
            rel = "src/data_sheets_schema/address_adapter_4588.py"
            self.assertIn(("VOICE", 2), self._violations(root, rel, derived, spans))
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("address_adapter_4588", off)

    def test_entry_address_conversion_keeps_nested_argument_effect_refusal_4588(self):
        adapter = ('from external_mutator import fill\n'
                   'def select_address(value):\n    return Path(value)\n')
        content = ('def content(record_path):\n'
                   '    record_path = select_address(fill(record_path))\n'
                   '    return f"Use the neutral record at {record_path}."\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._address_adapter_root_4588(directory, adapter, content=content)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_entry_address_proof_rejects_unknown_factory_and_later_rebinding_4588(self):
        cases = (
            ('from external_factory import make_address\n'
             'def select_address(value):\n    return make_address(value)\n',
             '    record_path = select_address(record_path)\n'),
            ('from external_factory import make_address\n'
             'def select_address(value):\n    return Path(value)\n',
             '    record_path = select_address(record_path)\n'
             '    record_path = make_address(record_path)\n'),
        )
        for adapter, initialization in cases:
            with self.subTest(initialization=initialization), tempfile.TemporaryDirectory() as directory:
                content = ('def content(record_path):\n' + initialization +
                           '    return f"Use the neutral record at {record_path}."\n')
                root = self._address_adapter_root_4588(directory, adapter, content=content)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                self._derive(root, sinks=False)


    def _destructive_formal_fixture_4733(self, directory, initial, body):
        """A resolved helper receives the exact container subsequently sent to PhaseRequest."""
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\n"
            "from data_sheets_schema import destructive_formal_4733 as operations\n"
            "from data_sheets_schema import destructive_text_4733 as policy\n")
        marker = "    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,"
        self.assertEqual(runner.count(marker), 1)
        runner = runner.replace(
            marker,
            "    parts = " + initial + "\n    operations.mutate(parts)\n" + marker,
        )
        runner = runner.replace("[guide, value, ids_4085.label(spec)]", "[parts]")
        modules = dict(PRECISION_MODULES)
        modules["destructive_formal_4733"] = (
            "from data_sheets_schema import destructive_text_4733 as policy\n\n"
            "def mutate(items):\n" + body)
        modules["destructive_text_4733"] = (
            'TEXT = "Describe the CHORUS cohort from its source records."\n'
            'ASIDE = "A VOICE aside this module never sends."\n'
        )
        root = self._root(directory, runner, modules)
        off, off_spans, _ = self._derive(root, sinks=False)
        self.assertNotIn("destructive_formal_4733", off)
        self.assertNotIn("destructive_text_4733", off)
        self.assertEqual(self._violations(
            root, "src/data_sheets_schema/destructive_text_4733.py", off, off_spans), set())
        return root

    def test_destructive_list_formals_refuse_unmodeled_deletion_4733(self):
        for call in ("items.clear()", "items.pop()", "items.remove('CHORUS')"):
            with self.subTest(call=call), tempfile.TemporaryDirectory() as directory:
                body = f"    {call}\n    return items\n"
                root = self._destructive_formal_fixture_4733(
                    directory, '["CHORUS", "VOICE"]', body)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_destructive_dict_formals_refuse_unmodeled_deletion_4733(self):
        for call in ("items.clear()", "items.pop('k')", "items.popitem()"):
            with self.subTest(call=call), tempfile.TemporaryDirectory() as directory:
                body = f"    {call}\n    return items\n"
                root = self._destructive_formal_fixture_4733(
                    directory, '{"k": "CHORUS", "other": "VOICE"}', body)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_supported_formal_append_and_get_keep_real_text_4733(self):
        """The correction preserves modeled append and nonmutating dict get."""
        cases = (
            ("append", "[]", "    items.append(policy.TEXT)\n"),
            ("get", "{'text': policy.TEXT}", "    items.get('text')\n"),
        )
        for label, initial, body in cases:
            with self.subTest(operation=label), tempfile.TemporaryDirectory() as directory:
                root = self._destructive_formal_fixture_4733(directory, initial, body)
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertIn("destructive_text_4733", derived)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/destructive_text_4733.py", derived, spans),
                    {("CHORUS", 1), ("VOICE", 2)})


    def _carried_projection_root_4588(self, directory, body, helpers):
        runner = PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import projection_client_4588\n")
        runner = runner.replace(
            "[guide, value, ids_4085.label(spec)]", "[projection_client_4588.content(spec)]")
        modules = dict(PRECISION_MODULES)
        modules["projection_helpers_4588"] = helpers
        modules["projection_client_4588"] = (
            'ASIDE = "A VOICE aside this function never sends."\n'
            "import json\n"
            "from data_sheets_schema import projection_helpers_4588 as helpers\n\n"
            "def content(spec):\n" + body + "\n"
        )
        return self._root(directory, runner, modules)

    def test_resolved_helper_emits_caller_inline_mapping_keys_4588(self):
        helpers = (
            "import json\n"
            "def encode(mapping):\n"
            "    return json.dumps(mapping)\n"
        )
        mapping = '{"Neutral instruction sentence": "v"}'
        with tempfile.TemporaryDirectory() as d:
            root = self._carried_projection_root_4588(
                d,
                "    return helpers.encode(" + mapping + ")\n",
                helpers,
            )
            derived, spans, _ = self._derive(root)
            self.assertIn("projection_client_4588", derived)
            self.assertEqual(
                self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                {("VOICE", 1)},
            )

    def test_imported_mapping_key_retains_historical_constant_promotion_4588(self):
        helpers = (
            "import json\n"
            "def encode(mapping):\n"
            "    return json.dumps(mapping)\n"
        )
        with tempfile.TemporaryDirectory() as d:
            root = self._carried_projection_root_4588(
                d,
                "    from data_sheets_schema import keys_4405\n"
                '    return helpers.encode({keys_4405.KEY: "v"})\n',
                helpers,
            )
            _write(root / "src/data_sheets_schema/keys_4405.py", 'KEY = "Describe the VOICE cohort."\n')
            derived, spans, _ = self._derive(root)
            self.assertIn("keys_4405", derived)
            self.assertEqual(
                self._violations(root, "src/data_sheets_schema/keys_4405.py", derived, spans),
                {("VOICE", 1)},
            )

    def test_helper_values_lookup_and_selected_inner_map_do_not_emit_outer_keys_4588(self):
        helpers = (
            "def select_inner(mapping):\n"
            '    return mapping["Neutral instruction sentence"]\n'
        )
        mapping = '{"Neutral instruction sentence": {"inner": "v"}}'
        for expr, expected in (
            ('helpers.select_inner(' + mapping + ')["inner"]', False),
            ('json.dumps(helpers.select_inner(' + mapping + '))', False),
            ('json.dumps(' + mapping + ')', True),
        ):
            with self.subTest(expr=expr), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(d, "    return " + expr + "\n", helpers)
                derived, spans, _ = self._derive(root)
                self.assertEqual(
                    self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                    {("VOICE", 1)} if expected else set(),
                )

    def test_helper_result_lookup_and_emission_keep_both_orders_4588(self):
        helpers = (
            "def identity(mapping):\n"
            "    return mapping\n"
        )
        mapping = '{"Neutral instruction sentence": "v"}'
        lookup = 'helpers.identity(' + mapping + ')["Neutral instruction sentence"]'
        emission = 'json.dumps(helpers.identity(' + mapping + '))'
        for expressions in ((lookup, emission), (emission, lookup)):
            with self.subTest(expressions=expressions), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(
                    d, '    return (' + ', '.join(expressions) + ')',
                    'def identity(mapping):\n    return mapping\n')
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertIn("projection_client_4588", derived)
                self.assertEqual(self._violations(
                    root, "src/data_sheets_schema/projection_client_4588.py", derived, spans), {("VOICE", 1)})

    def test_recursive_helper_projection_preserves_real_base_emission_in_both_orders_4588(self):
        first = ('def first(mapping, again=False):\n'
                 '    return second(mapping) if again else json.dumps(mapping)\n')
        second = ('def second(mapping, again=False):\n'
                  '    return first(mapping) if again else "{}"\n')
        for definitions in ((first, second), (second, first)):
            with self.subTest(first_definition=definitions[0].splitlines()[0]), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(
                    d, '    return helpers.first(mapping={"Neutral instruction sentence": "v"})',
                    '\n'.join(definitions))
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertIn("projection_client_4588", derived)
                rel = "src/data_sheets_schema/projection_client_4588.py"
                self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 1)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("projection_client_4588", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())


    def _json_module_alias_root_trace(self, directory, prefix, expression):
        helper = ('from data_sheets_schema import json_alias_policy_trace as policy\n\n'
                  'def replacement(mapping):\n'
                  '    mapping["late"] = policy.TEXT\n'
                  '    return policy.TEXT\n')
        body = (prefix + '    mapping = {"Neutral instruction sentence": spec.value}\n'
                '    return ' + expression + '(mapping)')
        return self._inline_key_context_fixture(directory, body, {
            "key_factory_trace": helper,
            "json_alias_policy_trace": (
                'TEXT = "Describe the CHORUS cohort from source records."\n'
                'ASIDE = "A VOICE aside this replacement never sends."\n'),
        })

    def test_json_second_module_import_attribute_write_revokes_summary_trace(self):
        """Two actual imports share a module even when lexical root names differ."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    import json as other\n'
                '    other.dumps = key_factory_trace.replacement\n', 'json.dumps')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("json_alias_policy_trace", off)

    def test_json_direct_module_alias_attribute_write_revokes_summary_trace(self):
        """An explicit ordinary Name alias carries the same module attribute write."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    other = json\n'
                '    other.dumps = key_factory_trace.replacement\n', 'json.dumps')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("json_alias_policy_trace", off)

    def test_json_from_import_after_module_write_is_not_original_function_trace(self):
        """A later from-import captures the explicitly replaced module attribute."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    import json as other\n'
                '    other.dumps = key_factory_trace.replacement\n'
                '    from json import dumps as encode\n', 'encode')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("json_alias_policy_trace", off)

    def test_json_function_local_capture_before_write_refuses_unproven_freshness_trace(self):
        """A function-local import can recapture a prior invocation's replacement."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    from json import dumps as encode\n'
                '    import json as other\n'
                '    other.dumps = key_factory_trace.replacement\n', 'encode')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("key_context_trace", off)


    def test_json_captured_function_name_reassignment_still_refuses_trace(self):
        """Rebinding the captured name itself differs from changing its old module."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    from json import dumps as encode\n'
                '    encode = key_factory_trace.replacement\n', 'encode')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("json_alias_policy_trace", off)


    def test_json_module_alias_chain_and_deletion_revoke_summary_trace(self):
        cases = {
            "chain": ('    first = json\n'
                      '    second = first\n'
                      '    second.dumps = key_factory_trace.replacement\n'),
            "deletion": ('    import json as other\n'
                         '    del other.dumps\n'),
        }
        for name, prefix in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = self._json_module_alias_root_trace(d, prefix, 'json.dumps')
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("json_alias_policy_trace", off)

    def test_json_unrelated_nested_local_alias_name_does_not_rebind_module_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    import json as other\n'
                '    def unused():\n'
                '        other = key_factory_trace\n'
                '        other.dumps = key_factory_trace.replacement\n', 'json.dumps')
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertIn("key_context_trace", derived)
            self.assertNotIn("json_alias_policy_trace", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("key_context_trace", off)


    def test_json_local_capture_before_write_repeated_calls_are_not_fresh_trace(self):
        """The first real source call replaces JSON; the second imports that replacement."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    from json import dumps as encode\n'
                '    import json as other\n'
                '    other.dumps = key_factory_trace.replacement\n', 'encode')
            runner = root / scan.RUNNER
            text = runner.read_text(encoding="utf-8")
            one = '[key_context_trace.content(spec)]'
            self.assertEqual(text.count(one), 1)
            runner.write_text(text.replace(one,
                '[key_context_trace.content(spec), key_context_trace.content(spec)]'),
                encoding="utf-8")
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("json_alias_policy_trace", off)

    def test_json_module_capture_before_function_write_survives_repeated_calls_trace(self):
        """A module-level captured function is not re-imported on the second call."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    import json as other\n'
                '    other.dumps = key_factory_trace.replacement\n', 'encode')
            module = root / 'src/data_sheets_schema/key_context_trace.py'
            text = module.read_text(encoding="utf-8")
            self.assertEqual(text.count('import json\n'), 1)
            module.write_text(text.replace('import json\n',
                'import json\nfrom json import dumps as encode\n', 1), encoding="utf-8")
            runner = root / scan.RUNNER
            text = runner.read_text(encoding="utf-8")
            one = '[key_context_trace.content(spec)]'
            self.assertEqual(text.count(one), 1)
            runner.write_text(text.replace(one,
                '[key_context_trace.content(spec), key_context_trace.content(spec)]'),
                encoding="utf-8")
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertIn("key_context_trace", derived)
            self.assertNotIn("json_alias_policy_trace", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("key_context_trace", off)
            self.assertNotIn("json_alias_policy_trace", off)

    def test_rebound_projection_helper_keeps_conservative_outer_key_emission_4733(self):
        """Rebound helpers must not use a stale projection summary."""
        helpers = (
            'import json\n'
            'def select(mapping):\n'
            '    return mapping["inner"]\n'
            'select = json.dumps\n'
        )
        mapping = '{"Neutral instruction sentence": "v", "inner": "ok"}'
        with tempfile.TemporaryDirectory() as d:
            root = self._carried_projection_root_4588(
                d,
                '    return helpers.select(' + mapping + ')\n',
                helpers,
            )
            derived, spans, _ = self._derive(root)
            self.assertIn("projection_client_4588", derived)
            self.assertEqual(
                self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                {("VOICE", 1)},
            )

    def test_decorated_projection_helper_keeps_conservative_outer_key_emission_4733(self):
        """Decorated helpers must not be treated as pure mapping projections."""
        helpers = (
            'import json\n'
            'def wraps(fn):\n'
            '    return json.dumps\n'
            '@wraps\n'
            'def select(mapping):\n'
            '    return mapping["inner"]\n'
        )
        mapping = '{"Neutral instruction sentence": "v", "inner": "ok"}'
        with tempfile.TemporaryDirectory() as d:
            root = self._carried_projection_root_4588(
                d,
                '    return helpers.select(' + mapping + ')\n',
                helpers,
            )
            derived, spans, _ = self._derive(root)
            self.assertIn("projection_client_4588", derived)
            self.assertEqual(
                self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                {("VOICE", 1)},
            )
    def test_ambiguous_nested_projection_keeps_keyword_text_in_both_orders_4733(self):
        """Ambiguous nested helper calls keep keyword/outer mapping text in both orders."""
        first = (
            'def outer(mapping):\n'
            '    return inner(mapping)\n'
        )
        second = (
            'import json\n'
            'def inner(mapping):\n'
            '    return json.dumps(mapping)\n'
        )
        mapping = '{"Neutral instruction sentence": "v"}'
        for label, helpers in (("outer_first", first + second), ("inner_first", second + first)):
            with self.subTest(order=label), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(
                    d,
                    '    return helpers.outer(mapping=' + mapping + ')\n',
                    helpers,
                )
                derived, spans, _ = self._derive(root)
                self.assertIn("projection_client_4588", derived)
                self.assertEqual(
                    self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                    {("VOICE", 1)},
                )
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("projection_client_4588", off)


    def test_authentic_nested_projection_preserves_selected_mapping_depth_4733(self):
        helpers = (
            'def inner(mapping):\n'
            '    return mapping["a"]\n'
            'def outer(mapping):\n'
            '    return inner(mapping)["b"]\n'
        )
        mapping = '{"a": {"b": {"Neutral instruction sentence": "v"}}}'
        for label, expr, expected in (
            ("selected_leaf", 'helpers.outer(' + mapping + ')["Neutral instruction sentence"]', False),
            ("serialized_submap", 'json.dumps(helpers.outer(' + mapping + '))', True),
        ):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(d, '    return ' + expr + '\n', helpers)
                derived, spans, _ = self._derive(root)
                self.assertEqual(
                    self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                    {("VOICE", 1)} if expected else set())
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("projection_client_4588", off)


    def test_json_module_formal_and_wrapped_alias_escapes_decline_summary_trace(self):
        cases = {
            "same_source_formal": '    mutate_json_module(json)\n',
            "wrapped_projection": ('    holders = [json]\n'
                                   '    holders[0].dumps = key_factory_trace.replacement\n'),
        }
        for label, prefix in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as d:
                root = self._json_module_alias_root_trace(d, prefix, 'json.dumps')
                module = root / 'src/data_sheets_schema/key_context_trace.py'
                _write(module, module.read_text(encoding='utf-8').replace(
                    'from data_sheets_schema import json_alias_policy_trace\n',
                    'from data_sheets_schema import json_alias_policy_trace, key_factory_trace\n'))
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("json_alias_policy_trace", off)

    def test_json_direct_alias_and_member_calls_do_not_escape_module_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    other = json\n'
                '    metadata = other.dumps({"meta": 1})\n'
                '    decoded = json.loads("{}")\n', 'json.dumps')
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertIn("key_context_trace", derived)
            self.assertNotIn("json_alias_policy_trace", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("key_context_trace", off)


    def test_json_mixed_chained_alias_does_not_hide_projected_escape_trace(self):
        """One direct alias target cannot hide the same module stored in a list."""
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    holders = [None]\n'
                '    other = holders[0] = json\n'
                '    holders[0].dumps = key_factory_trace.replacement\n', 'json.dumps')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("json_alias_policy_trace", off)


    def test_recursive_selected_branch_keeps_real_base_mapping_keys_4588(self):
        """A dormant recursive lookup cannot prevent the actual base mapping from emitting."""
        helpers = ('def encode(mapping, again=False):\n'
                   '    return encode(mapping, False)["x"] if again else mapping\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._carried_projection_root_4588(
                d, '    return json.dumps(helpers.encode({"Neutral instruction sentence": "v", '
                '"x": {"neutral": "v"}}))', helpers)
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertEqual(facts["request"]["class"], "PhaseRequest")
            self.assertIn("projection_client_4588", derived)
            rel = "src/data_sheets_schema/projection_client_4588.py"
            self.assertEqual(self._violations(root, rel, derived, spans), {("VOICE", 1)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn("projection_client_4588", off)
            self.assertEqual(self._violations(root, rel, off, off_spans), set())

    def test_recursive_projection_keeps_independent_caller_depth_in_both_orders_4588(self):
        """A shallow call without prose cannot donate key-emission depth to a deeper call."""
        helpers = ('def encode(mapping, again=False):\n'
                   '    return encode(mapping, False)["x"] if again else mapping\n')
        mapping = '{"x": {"Neutral instruction sentence": "v"}}'
        shallow = 'helpers.encode(' + mapping + ', False)["x"]["Neutral instruction sentence"]'
        deep = 'json.dumps(helpers.encode(' + mapping + ', True))'
        for label, expressions in (("shallow_then_deep", (shallow, deep)), ("deep_then_shallow", (deep, shallow))):
            with self.subTest(order=label), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(
                    d, '    return (' + ', '.join(expressions) + ')\n', helpers)
                derived, spans, _ = self._derive(root)
                self.assertIn("projection_client_4588", derived)
                self.assertEqual(
                    self._violations(
                        root,
                        "src/data_sheets_schema/projection_client_4588.py",
                        derived,
                        spans,
                    ),
                    {("VOICE", 1)},
                )
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("projection_client_4588", off)

    def test_json_namespace_and_captured_function_mutation_decline_identity_trace(self):
        cases = {
            "module_dict": ('    namespace = json.__dict__\n'
                            '    namespace["dumps"] = key_factory_trace.literal_replacement\n'),
            "captured_code": ('    captured = json.dumps\n'
                              '    alias = captured\n'
                              '    alias.__code__ = key_factory_trace.literal_replacement.__code__\n'),
        }
        for label, prefix in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as d:
                root = self._json_module_alias_root_trace(d, prefix, 'json.dumps')
                module = root / 'src/data_sheets_schema/key_context_trace.py'
                _write(module, module.read_text(encoding='utf-8').replace(
                    'from data_sheets_schema import json_alias_policy_trace\n',
                    'from data_sheets_schema import json_alias_policy_trace, key_factory_trace\n'))
                _write(root / 'src/data_sheets_schema/key_factory_trace.py', 'def literal_replacement(*_a, **_kw):\n    return "ok"\n')
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_context_trace", off)
                self.assertNotIn("json_alias_policy_trace", off)

    def test_json_exception_type_reads_preserve_module_identity_trace(self):
        cases = {
            "member": ('', 'json.JSONDecodeError'),
            "import": ('    from json import JSONDecodeError as DecodeError\n', 'DecodeError'),
        }
        for name, (prefix, caught) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = self._json_module_alias_root_trace(d,
                    prefix + '    try:\n'
                    '        metadata = json.loads("{}")\n'
                    '    except (ValueError, ' + caught + '):\n'
                    '        metadata = None\n', 'json.dumps')
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertIn("key_context_trace", derived)
                self.assertNotIn("json_alias_policy_trace", derived)
                self.assertEqual(self._violations(root,
                    "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("key_context_trace", off)
                self.assertNotIn("json_alias_policy_trace", off)

    def test_mutual_lookup_recursion_transfers_exact_actual_formals_4588(self):
        first = ('def first(left, right, swap=True):\n'
                 '    return second(first_arg=left, second_arg=right) if swap else left["k"]\n')
        second = ('def second(first_arg, second_arg):\n'
                  '    return first(left=second_arg, right=first_arg, swap=False)\n')
        mapping = '{"k": {"Neutral instruction sentence": "v"}}'
        for order, helpers in (("first_second", first + second), ("second_first", second + first)):
            for target, right_arg, expected in (
                ("emitted_right", mapping, True),
                ("neutral_right", '{"k": {"neutral": "v"}}', False),
            ):
                with self.subTest(order=order, target=target), tempfile.TemporaryDirectory() as d:
                    root = self._carried_projection_root_4588(
                        d, '    return json.dumps(helpers.first(left={"neutral": "v"}, right=' +
                        right_arg + '))\n',
                        helpers)
                    derived, spans, _ = self._derive(root)
                    if expected:
                        self.assertIn("projection_client_4588", derived)
                    else:
                        self.assertNotIn("projection_client_4588", derived)
                    self.assertEqual(
                        self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                        {("VOICE", 1)} if expected else set())
                    off, _, _ = self._derive(root, sinks=False)
                    self.assertNotIn("projection_client_4588", off)
    def test_constructed_recursive_result_preserves_base_keys_and_values_only_4588(self):
        helpers = ('def encode(mapping, depth=0):\n'
                   '    return {"outer": encode(mapping, depth - 1)} if depth > 0 else mapping\n')
        mapping = '{"Neutral instruction sentence": "v"}'
        for label, expr, expected in (
            ('base_json', 'json.dumps(helpers.encode(' + mapping + '))', True),
            ('selected_inner', 'helpers.encode(' + mapping + ', 1)["outer"]["Neutral instruction sentence"]', False),
            ('emitted_wrapped', 'json.dumps(helpers.encode(' + mapping + ', 1))', True),
        ):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(
                    d, '    return ' + expr + '\n', helpers)
                derived, spans, _ = self._derive(root)
                if expected:
                    self.assertIn("projection_client_4588", derived)
                else:
                    self.assertNotIn("projection_client_4588", derived)
                self.assertEqual(
                    self._violations(root, "src/data_sheets_schema/projection_client_4588.py", derived, spans),
                    {("VOICE", 1)} if expected else set())
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn("projection_client_4588", off)

    def test_json_imported_noarg_helper_shared_module_write_declines_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    from data_sheets_schema.json_shared_patch_trace import install\n'
                '    install()\n', 'json.dumps')
            _write(root / 'src/data_sheets_schema/json_shared_patch_trace.py',
                'import json\n'
                'from data_sheets_schema import key_factory_trace\n'
                'def install():\n'
                '    json.dumps = key_factory_trace.replacement\n')
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("key_context_trace", off)
            self.assertNotIn("json_alias_policy_trace", off)

    def test_json_imported_noarg_helper_ordinary_member_use_preserves_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._json_module_alias_root_trace(d,
                '    from data_sheets_schema.json_shared_patch_trace import inspect_metadata\n'
                '    inspect_metadata()\n', 'json.dumps')
            _write(root / 'src/data_sheets_schema/json_shared_patch_trace.py',
                'import json\n'
                'def inspect_metadata():\n'
                '    return json.dumps({"metadata": 1})\n')
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertIn("key_context_trace", derived)
            self.assertNotIn("json_alias_policy_trace", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/key_context_trace.py", derived, spans), {("VOICE", 1)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn("key_context_trace", off)
    def test_json_literal_options_keep_real_renderspec_text_4733(self):
        """The actual record serializer options preserve emitted mapping text."""
        cases = (
            ('recording', '', 'json.dumps', ', sort_keys=True, separators=(",", ":")'),
            ('metadata', '', 'json.dumps', ', ensure_ascii=False, sort_keys=True'),
            ('imported', '    from json import dumps as encode\n', 'encode',
             ', ensure_ascii=True, sort_keys=False, separators=(", ", ": ")'),
        )
        for route, imports, callee, options in cases:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                root = self._inline_key_context_fixture(directory,
                    imports + '    mapping = {"Neutral instruction sentence": spec.value}\n'
                    '    return ' + callee + '(mapping' + options + ')')
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts['requests'])
                self.assertIn('key_context_trace', derived)
                path = 'src/data_sheets_schema/key_context_trace.py'
                self.assertEqual(self._violations(root, path, derived, spans), {('VOICE', 1)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn('key_context_trace', off)
                self.assertEqual(self._violations(root, path, off, off_spans), set())

    def test_json_literal_separator_is_emitted_text_not_an_ignored_option_4733(self):
        """Two entries really emit the item separator, including its inline prose."""
        with tempfile.TemporaryDirectory() as directory:
            root = self._inline_key_context_fixture(directory,
                '    mapping = {"first": 1, "second": 2}\n'
                '    return json.dumps(mapping, separators=("Neutral instruction sentence", ":"))')
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts['requests'])
            self.assertIn('key_context_trace', derived)
            path = 'src/data_sheets_schema/key_context_trace.py'
            self.assertEqual(self._violations(root, path, derived, spans), {('VOICE', 1)})
            off, off_spans, _ = self._derive(root, sinks=False)
            self.assertNotIn('key_context_trace', off)
            self.assertEqual(self._violations(root, path, off, off_spans), set())

    def test_json_literal_options_keep_callbacks_mutations_and_identity_refusal_4733(self):
        """Literal formatting does not admit callbacks, spreads or changed serializer identity."""
        helper = ('from data_sheets_schema import json_policy_trace as policy\n\n'
                  'def mutate(mapping):\n'
                  '    mapping["late"] = policy.TEXT\n'
                  '    return True\n\n'
                  'def convert(value):\n'
                  '    return policy.TEXT\n\n'
                  'def dumps(mapping, **options):\n'
                  '    mapping["late"] = policy.TEXT\n'
                  '    return mapping\n')
        cases = (
            ('callback', '', ', sort_keys=True, default=key_factory_trace.convert'),
            ('nested_mutation', '', ', sort_keys=key_factory_trace.mutate(mapping)'),
            ('spread', '', ', **{"sort_keys": True}'),
            ('nonboolean', '', ', sort_keys=1'),
            ('replaced_identity', '    json.dumps = key_factory_trace.dumps\n', ', sort_keys=True'),
        )
        for route, prefix, options in cases:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                root = self._inline_key_context_fixture(directory,
                    '    mapping = {"neutral": spec.value}\n' + prefix +
                    '    return json.dumps(mapping' + options + ')',
                    {'key_factory_trace': helper,
                     'json_policy_trace': 'TEXT = "Describe the CHORUS cohort."\n'})
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('json_policy_trace', off)


    def test_depth_contracting_recursive_result_keeps_keys_and_values_only_4588(self):
        helpers = ('def encode(mapping, again=False):\n'
                   '    return {"x": encode(mapping, False)} if again else mapping\n')
        mapping = '{"Neutral instruction sentence": "v"}'
        selected = 'helpers.encode(' + mapping + ', True)["x"]'
        cases = (
            ('one_real_wrap_then_json', 'json.dumps(' + selected + ')', True),
            ('one_real_wrap_then_value', selected + '["Neutral instruction sentence"]', False),
        )
        for route, expression, emitted in cases:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as d:
                root = self._carried_projection_root_4588(d, '    return ' + expression, helpers)
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts["requests"])
                self.assertEqual("projection_client_4588" in derived, emitted)
                rel = "src/data_sheets_schema/projection_client_4588.py"
                self.assertEqual(self._violations(root, rel, derived, spans),
                                 {("VOICE", 1)} if emitted else set())
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn("projection_client_4588", off)
                self.assertEqual(self._violations(root, rel, off, off_spans), set())


    def test_json_source_dependencies_revoke_cross_file_identity_root(self):
        replacement = ('import json\n'
                       'def replacement(mapping):\n'
                       '    mapping["late"] = "Describe the CHORUS cohort."\n'
                       '    return "replacement"\n')
        for route in ('own_package_initializer', 'transitive_helper', 'import_time_write'):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                root = self._inline_key_context_fixture(directory,
                    '    mapping = {"Neutral instruction sentence": spec.value}\n'
                    '    return json.dumps(mapping)')
                client = root / 'src/data_sheets_schema/key_context_trace.py'
                client.write_text(client.read_text().replace(
                    'from data_sheets_schema import key_factory_trace\n', ''))
                if route == 'own_package_initializer':
                    _write(root / 'src/data_sheets_schema/__init__.py',
                           replacement + 'json.dumps = replacement\n')
                elif route == 'transitive_helper':
                    _write(root / 'src/data_sheets_schema/closure_patch_root.py', replacement +
                           'def install():\n    json.dumps = replacement\n')
                    _write(root / 'src/data_sheets_schema/closure_bridge_root.py',
                           'from .closure_patch_root import install\n')
                    client.write_text(client.read_text().replace('    mapping =',
                        '    from .closure_bridge_root import install\n    install()\n    mapping ='))
                else:
                    _write(root / 'src/data_sheets_schema/closure_patch_root.py',
                           replacement + 'json.dumps = replacement\n')
                    client.write_text(client.read_text().replace('import json\n',
                        'import json\nfrom . import closure_patch_root\n'))
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, facts = self._derive(root, sinks=False)
                self.assertTrue(facts['requests'])
                self.assertNotIn('key_context_trace', off)

    def test_json_source_dependencies_keep_readonly_cycles_and_unrelated_files_root(self):
        for route in ('ordinary_initializer', 'import_cycle', 'unimported_mutator'):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                root = self._inline_key_context_fixture(directory,
                    '    mapping = {"Neutral instruction sentence": spec.value}\n'
                    '    return json.dumps(mapping)')
                client = root / 'src/data_sheets_schema/key_context_trace.py'
                client.write_text(client.read_text().replace(
                    'from data_sheets_schema import key_factory_trace\n', ''))
                if route == 'ordinary_initializer':
                    _write(root / 'src/data_sheets_schema/__init__.py',
                           'import json\nMETADATA = json.dumps({"metadata": 1})\n')
                elif route == 'import_cycle':
                    _write(root / 'src/data_sheets_schema/closure_bridge_root.py',
                           'from . import key_context_trace\nimport json\n'
                           'def inspect_metadata():\n    return json.dumps({"metadata": 1})\n')
                    client.write_text(client.read_text().replace('    mapping =',
                        '    from .closure_bridge_root import inspect_metadata\n'
                        '    inspect_metadata()\n    mapping ='))
                else:
                    _write(root / 'src/data_sheets_schema/unimported_json_mutator_root.py',
                           'import json\njson.dumps = lambda mapping: "replacement"\n')
                derived, spans, facts = self._derive(root)
                self.assertTrue(facts['requests'])
                self.assertIn('key_context_trace', derived)
                self.assertEqual(self._violations(root,
                    'src/data_sheets_schema/key_context_trace.py', derived, spans), {('VOICE', 1)})
                off, off_spans, _ = self._derive(root, sinks=False)
                self.assertNotIn('key_context_trace', off)
                self.assertEqual(self._violations(root,
                    'src/data_sheets_schema/key_context_trace.py', off, off_spans), set())


    def test_definition_time_function_defaults_refuse_unknown_mutation_root(self):
        cases = ('    def install(value=fill(parts)):\n        pass',
                 '    def install(*, value=fill(parts)):\n        pass',
                 '    async def install(value=fill(parts)):\n        pass',
                 '    install = lambda value=fill(parts): None')
        for definition in cases:
            with self.subTest(definition=definition), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n' + definition)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('predicate_text_4733', off)

    def test_definition_time_decorator_refuses_unknown_mutation_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._predicate_boundary_root_4733(directory,
                '    parts = [predicate_text.TEXT]\n'
                '    @fill(parts)\n    def install():\n        pass')
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_definition_time_class_headers_refuse_unknown_mutation_root(self):
        for header in ('class Install(fill(parts)):', 'class Install(metaclass=fill(parts)):'):
            with self.subTest(header=header), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n    ' + header + '\n        pass')
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                self._derive(root, sinks=False)

    def test_definition_time_class_body_refuses_unknown_mutation_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._predicate_boundary_root_4733(directory,
                '    parts = [predicate_text.TEXT]\n'
                '    class Install:\n        fill(parts)')
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            self._derive(root, sinks=False)

    def test_definition_time_eager_annotation_refuses_unknown_mutation_root(self):
        for body in ('    class Install:\n        value: fill(parts) = 1', '    def method(value: fill(parts)):\n        return value'):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n' + body)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                self._derive(root, sinks=False)

    def test_unexecuted_nested_bodies_and_postponed_annotations_remain_supported_root(self):
        for label, prefix, body in (
                ('nested', '', '    class Install:\n        def method(self):\n            fill(parts)'),
                ('postponed', 'from __future__ import annotations\n', '    def method(value: fill(parts)):\n        return value'),
        ):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n' + body,
                    prefix=prefix)
                derived, spans, facts = self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('predicate_text_4733', off)
                self.assertTrue(facts['requests'])
                self.assertIn('predicate_text_4733', derived)
                self.assertEqual(self._violations(root,
                    'src/data_sheets_schema/predicate_text_4733.py', derived, spans), {('VOICE', 2)})
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('predicate_text_4733', off)


    def test_function_local_annotation_does_not_execute_unknown_mutation_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._predicate_boundary_root_4733(directory,
                '    parts = [predicate_text.TEXT]\n    value: fill(parts)')
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts['requests'])
            self.assertIn('predicate_text_4733', derived)
            self.assertEqual(self._violations(root,
                'src/data_sheets_schema/predicate_text_4733.py', derived, spans), {('VOICE', 2)})
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn('predicate_text_4733', off)

    def test_class_annotation_execution_respects_future_declaration_root(self):
        for postponed in (False, True):
            with self.subTest(postponed=postponed), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n    class Install:\n        value: fill(parts)')
                if postponed:
                    runner = root / scan.RUNNER
                    runner.write_text('from __future__ import annotations\n' + runner.read_text())
                    derived, _, facts = self._derive(root)
                    self.assertTrue(facts['requests'])
                    self.assertIn('predicate_text_4733', derived)
                else:
                    with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                        self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('predicate_text_4733', off)


    def _request_boundary_fixture_4588(self, directory, client):
        modules = dict(PRECISION_MODULES)
        modules["request_boundary_4588"] = client
        modules["request_policy_4588"] = (
            'TEXT = "Describe the CHORUS record using its source evidence."\n'
            'ASIDE = "An unused VOICE editorial aside."\n')
        return self._root(directory, PRECISION_RUNNER, modules)

    def test_shadowed_request_bindings_do_not_certify_diagnostic_calls_4588(self):
        sources = (
            ('local_name',
             'from data_sheets_schema.api_runner import PhaseRequest\n'
             'def inspect():\n'
             '    PhaseRequest = lambda **fields: None\n'
             '    return PhaseRequest(system="Describe this diagnostic record only.")\n'),
            ('formal_name',
             'from data_sheets_schema.api_runner import PhaseRequest\n'
             'def inspect(PhaseRequest):\n'
             '    return PhaseRequest(system="Describe this diagnostic record only.")\n'),
            ('local_module',
             'from data_sheets_schema import api_runner as request_api\n'
             'class Diagnostics:\n'
             '    def PhaseRequest(self, **fields):\n        return None\n'
             'def inspect():\n'
             '    request_api = Diagnostics()\n'
             '    return request_api.PhaseRequest(system="Describe this diagnostic record only.")\n'),
            ('formal_module',
             'from data_sheets_schema import api_runner as request_api\n'
             'def inspect(request_api):\n'
             '    return request_api.PhaseRequest(system="Describe this diagnostic record only.")\n'),
        )
        expected_line = PRECISION_RUNNER.splitlines().index(
            '    return PhaseRequest(phase=phase, system=prompts_4085.SYSTEM,') + 1
        for binding, source in sources:
            with self.subTest(binding=binding), tempfile.TemporaryDirectory() as d:
                root = self._request_boundary_fixture_4588(d, source)
                derived, spans, facts = self._derive(root)
                self.assertEqual(facts["requests"], [f"{scan.RUNNER}:{expected_line}"])
                self.assertIn("prompts_4085", derived)
                self.assertNotIn("request_boundary_4588", derived)
                off, _, off_facts = self._derive(root, sinks=False)
                self.assertEqual(off_facts["requests"], facts["requests"])
                self.assertNotIn("request_boundary_4588", off)

    def test_shadowed_receiver_before_genuine_request_still_refuses_4588(self):
        source = ('from data_sheets_schema.api_runner import PhaseRequest\n'
                  'from data_sheets_schema import api_runner as actual_request_api\n'
                  'from external_request_mutator_4588 import fill\n'
                  'def make_request():\n'
                  '    PhaseRequest = fill\n'
                  '    parts = []\n'
                  '    PhaseRequest(messages=parts)\n'
                  '    return actual_request_api.PhaseRequest(phase="generation",\n'
                  '        system="Describe this source record.", messages=parts)\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._request_boundary_fixture_4588(d, source)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, facts = self._derive(root, sinks=False)
            self.assertTrue(facts["requests"])
            self.assertNotIn("request_boundary_4588", off)

    def test_unknown_request_spread_carriers_do_not_gain_terminal_authority_4588(self):
        for expansion, factory in (("*payload", "make_arguments"),
                                   ("**payload", "make_keywords")):
            source = ('from data_sheets_schema.api_runner import PhaseRequest\n'
                      'from external_request_carrier_4588 import ' + factory + '\n'
                      'def make_request():\n'
                      '    payload = ' + factory + '()\n'
                      '    return PhaseRequest(' + expansion + ')\n')
            with self.subTest(expansion=expansion), tempfile.TemporaryDirectory() as d:
                root = self._request_boundary_fixture_4588(d, source)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)
                off, _, facts = self._derive(root, sinks=False)
                self.assertTrue(facts["requests"])
                self.assertNotIn("request_boundary_4588", off)

    def test_exact_literal_request_spreads_keep_genuine_text_fields_4588(self):
        expansions = (
            '*("generation", policy.TEXT, [], [])',
            '**{"phase": "generation", "system": policy.TEXT, "messages": []}',
        )
        imports = (
            ('from data_sheets_schema.api_runner import PhaseRequest\n', 'PhaseRequest'),
            ('from data_sheets_schema import api_runner as request_api\n',
             'request_api.PhaseRequest'),
        )
        for expansion in expansions:
            for request_import, constructor in imports:
                source = (request_import +
                          'from data_sheets_schema import request_policy_4588 as policy\n'
                          'def make_request():\n'
                          '    return ' + constructor + '(' + expansion + ')\n')
                with self.subTest(expansion=expansion, constructor=constructor), \
                        tempfile.TemporaryDirectory() as d:
                    root = self._request_boundary_fixture_4588(d, source)
                    derived, spans, facts = self._derive(root)
                    self.assertEqual(len(facts["requests"]), 2)
                    self.assertIn("prompts_4085", derived)
                    self.assertIn("request_policy_4588", derived)
                    rel = "src/data_sheets_schema/request_policy_4588.py"
                    self.assertEqual(self._violations(root, rel, derived, spans),
                                     {("CHORUS", 1), ("VOICE", 2)})
                    off, _, off_facts = self._derive(root, sinks=False)
                    self.assertEqual(off_facts["requests"], facts["requests"])
                    self.assertNotIn("request_policy_4588", off)


    def _json_sheet_origin_root_trace(self, directory, *, reader_options="", update="", body=None, tuple_result=False):
        helper = ('from pathlib import Path\nimport json\n'
                  'from data_sheets_schema import json_sheet_policy_trace as policy\n'
                  'def load_sheet(path):\n'
                  '    record = json.loads(Path(path).read_text()' + reader_options + ')\n'
                  '    sheet = record.get("metadata", {}).get("healthsheet")\n'
                  '    if not sheet:\n        raise ValueError("missing healthsheet")\n'
                  '    return sheet, record\n'
                  'def render_sheet(sheet, record):\n' + update +
                  '    parts = [policy.TEXT, \"Render every source question faithfully.\"]\n'
                  '    for section, items in sheet.items():\n'
                  '        if not isinstance(items, list):\n            continue\n'
                  '        for item in items:\n'
                  '            parts.append(str(item.get("question", "")).strip())\n'
                  '    return " ".join(parts) + str(record.get("title", ""))\n')
        if tuple_result:
            helper = helper.replace('return " ".join(parts) + str(record.get("title", ""))',
                                    'return " ".join(parts) + str(record.get("title", "")), 0')
        return self._inline_key_context_fixture(directory, body or (
            '    sheet, record = key_factory_trace.load_sheet(spec.path)\n'
            '    return key_factory_trace.render_sheet(sheet, record)'), {
                "key_factory_trace": helper,
                "json_sheet_policy_trace": (
                    'TEXT = "Describe the CHORUS source questions faithfully."\n'
                    'ASIDE = "An unused VOICE editorial aside."\n'),
            })

    def test_json_decode_tuple_get_and_loop_origins_preserve_real_text_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._json_sheet_origin_root_trace(d)
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertIn("key_factory_trace", derived)
            self.assertIn("json_sheet_policy_trace", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/json_sheet_policy_trace.py", derived, spans),
                {("CHORUS", 1), ("VOICE", 2)})
            off, _, off_facts = self._derive(root, sinks=False)
            self.assertTrue(off_facts["requests"])
            self.assertNotIn("json_sheet_policy_trace", off)

    def test_json_origin_does_not_hide_shared_tree_writes_or_unknown_escapes_trace(self):
        changes = (
            '    sheet["late"] = policy.TEXT\n',
            '    alias = sheet\n    alias["late"] = policy.TEXT\n',
            '    from external_json_effect_trace import fill\n    fill(sheet)\n',
        )
        for update in changes:
            with self.subTest(update=update), tempfile.TemporaryDirectory() as d:
                root = self._json_sheet_origin_root_trace(d, update=update)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_json_equality_result_cannot_hide_a_shared_alias_trace(self):
        body = ('    from external_json_effect_trace import fill\n'
                '    record = json.loads("{}")\n'
                '    class ReflectedEquality:\n'
                '        def __eq__(self, other):\n            return other\n'
                '    alias = record == ReflectedEquality()\n'
                '    fill(alias)\n'
                '    return json.dumps(record)')
        with tempfile.TemporaryDirectory() as d:
            root = self._inline_key_context_fixture(d, body)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)

    def test_json_get_default_cannot_reuse_an_escaped_literal_origin_trace(self):
        for setup, fallback in (('fallback = {}; fill(fallback)', 'fallback'),
                                ('defaults = ({},); fill(defaults[0])', 'defaults[0]')):
            body = ('    from external_json_effect_trace import fill\n'
                    '    ' + setup + '\n'
                    '    record = json.loads("{}")\n'
                    '    selected = record.get("missing", ' + fallback + ')\n'
                    '    return json.dumps(selected)')
            with self.subTest(setup=setup), tempfile.TemporaryDirectory() as d:
                root = self._inline_key_context_fixture(d, body)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_json_origin_refuses_decode_hooks_and_unpack_before_unknown_call_trace(self):
        for options in (', object_hook=lambda value: value', ', cls=json.JSONDecoder'):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as d:
                root = self._json_sheet_origin_root_trace(d, reader_options=options)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_json_formal_facts_do_not_leak_to_unknown_callers_trace(self):
        for safe_first in (False, True):
            calls = ['key_factory_trace.render_sheet(sheet, record)',
                     'key_factory_trace.render_sheet(spec.unknown_sheet, record)']
            if not safe_first:
                calls.reverse()
            body = ('    sheet, record = key_factory_trace.load_sheet(spec.path)\n'
                    '    return [' + ', '.join(calls) + ']')
            with self.subTest(safe_first=safe_first), tempfile.TemporaryDirectory() as d:
                root = self._json_sheet_origin_root_trace(d, body=body)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_json_readonly_scalar_result_tuple_does_not_drop_input_facts_trace(self):
        body = ('    sheet, record = key_factory_trace.load_sheet(spec.path)\n'
                '    text, stats = key_factory_trace.render_sheet(sheet, record)\n'
                '    return text')
        with tempfile.TemporaryDirectory() as d:
            root = self._json_sheet_origin_root_trace(d, body=body, tuple_result=True)
            derived, spans, facts = self._derive(root)
            self.assertTrue(facts["requests"])
            self.assertIn("json_sheet_policy_trace", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/json_sheet_policy_trace.py", derived, spans),
                {("CHORUS", 1), ("VOICE", 2)})

    def test_json_origin_declines_shared_binding_and_nested_target_exports_trace(self):
        statements = (
            '    global saved\n    saved = record\n    touch_saved()\n',
            '    (holder.slot,) = (record,)\n    touch_saved()\n',
            '    global saved\n    for saved in record:\n        pass\n    touch_saved()\n',
        )
        for statement in statements:
            body = ('    from external_json_effect_trace import holder, touch_saved\n'
                    '    record = json.loads("[{}]")\n' + statement +
                    '    return json.dumps(record)')
            with self.subTest(statement=statement), tempfile.TemporaryDirectory() as d:
                root = self._inline_key_context_fixture(d, body)
                with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                    self._derive(root)

    def test_json_origin_recursive_tuple_packing_declines_finitely_trace(self):
        helper = ('def wrap(value, again=False):\n'
                  '    return wrap((value,), False) if again else value\n')
        body = ('    record = json.loads("{}")\n'
                '    wrapped = key_factory_trace.wrap(record, True)\n'
                '    return json.dumps(wrapped)')
        with tempfile.TemporaryDirectory() as d:
            root = self._inline_key_context_fixture(d, body, {"key_factory_trace": helper})
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect|recursive"):
                self._derive(root)


    def test_definition_time_implicit_decorators_and_metaclass_refuse_shared_container_root(self):
        definitions = (
            '    @fill\n    def install(value=parts):\n        pass',
            '    def decorate(fn):\n        fill(parts)\n        return fn\n'
            '    @decorate\n    def install():\n        pass',
            '    class Install(metaclass=fill):\n        value = parts',
            '    @fill\n    class Install:\n        value = parts',
        )
        for definition in definitions:
            with self.subTest(definition=definition), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n' + definition)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('predicate_text_4733', off)


    def test_equivalent_request_module_import_write_invalidates_diagnostic_sink_trace(self):
        source = ('from data_sheets_schema import api_runner as request_api\n'
                  'from data_sheets_schema import api_runner as other_api\n'
                  'def diagnostic(**fields):\n    return None\n'
                  'other_api.PhaseRequest = diagnostic\n'
                  'def inspect():\n'
                  '    return request_api.PhaseRequest(system="Describe this diagnostic record only.")\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._request_boundary_fixture_4588(d, source)
            derived, spans, facts = self._derive(root)
            self.assertFalse([row for row in facts["requests"]
                              if row.startswith("src/data_sheets_schema/request_boundary_4588.py:")])
            self.assertNotIn("request_boundary_4588", derived)
            off, _, off_facts = self._derive(root, sinks=False)
            self.assertEqual(off_facts["requests"], facts["requests"])
            self.assertNotIn("request_boundary_4588", off)

    def test_request_class_captured_before_namespace_replacement_keeps_identity_trace(self):
        source = ('from data_sheets_schema.api_runner import PhaseRequest as OriginalRequest\n'
                  'from data_sheets_schema import api_runner as other_api\n'
                  'from data_sheets_schema import request_policy_4588 as policy\n'
                  'def diagnostic(**fields):\n    return None\n'
                  'other_api.PhaseRequest = diagnostic\n'
                  'def inspect():\n'
                  '    return OriginalRequest(phase="generation", system=policy.TEXT)\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._request_boundary_fixture_4588(d, source)
            derived, spans, facts = self._derive(root)
            client = [row for row in facts["requests"]
                      if row.startswith("src/data_sheets_schema/request_boundary_4588.py:")]
            self.assertEqual(len(client), 1)
            self.assertIn("request_policy_4588", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/request_policy_4588.py", derived, spans),
                {("CHORUS", 1), ("VOICE", 2)})
            off, _, off_facts = self._derive(root, sinks=False)
            self.assertEqual(off_facts["requests"], facts["requests"])
            self.assertNotIn("request_policy_4588", off)

    def test_request_class_imported_after_namespace_replacement_has_no_identity_trace(self):
        source = ('from data_sheets_schema import api_runner as other_api\n'
                  'def diagnostic(**fields):\n    return None\n'
                  'other_api.PhaseRequest = diagnostic\n'
                  'from data_sheets_schema.api_runner import PhaseRequest as ReplacedRequest\n'
                  'from data_sheets_schema import request_policy_4588 as policy\n'
                  'def inspect():\n'
                  '    return ReplacedRequest(phase="generation", system=policy.TEXT)\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._request_boundary_fixture_4588(d, source)
            derived, spans, facts = self._derive(root)
            self.assertFalse([row for row in facts["requests"]
                              if row.startswith("src/data_sheets_schema/request_boundary_4588.py:")])
            self.assertNotIn("request_policy_4588", derived)
            off, _, off_facts = self._derive(root, sinks=False)
            self.assertEqual(off_facts["requests"], facts["requests"])
            self.assertNotIn("request_policy_4588", off)

    def test_implicit_definition_without_shared_carrier_keeps_real_text_root(self):
        for definition in ('    @fill\n    def install(value=42):\n        return value',
                           '    class Install(metaclass=fill):\n        value = 42'):
            with self.subTest(definition=definition), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n' + definition)
                derived, _, facts = self._derive(root)
                self.assertTrue(facts['requests'])
                self.assertIn('predicate_text_4733', derived)


    def test_implicit_decorator_alias_bindings_refuse_captured_container_root(self):
        definitions = (
            '    (decorate := mutate)\n    @decorate\n    def install():\n        pass',
            '    decorate, = (mutate,)\n    @decorate\n    def install():\n        pass',
            '    for decorate in (mutate,):\n        @decorate\n        def install():\n            pass',
            '    decorators = []\n    decorators.append(mutate)\n'
            '    @decorators[0]\n    def install():\n        pass',
            '    (decorators := [])\n    fill(decorators, mutate)\n'
            '    @decorators[0]\n    def install():\n        pass',
        )
        for definition in definitions:
            with self.subTest(definition=definition), tempfile.TemporaryDirectory() as directory:
                root = self._predicate_boundary_root_4733(directory,
                    '    parts = [predicate_text.TEXT]\n'
                    '    def mutate(fn):\n        fill(parts)\n        return fn\n' + definition)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                self._derive(root, sinks=False)


    def test_repeated_local_request_capture_has_no_fresh_identity_trace(self):
        source = ('from data_sheets_schema import api_runner as other_api\n'
                  'from data_sheets_schema import request_policy_4588 as policy\n'
                  'def diagnostic(**fields):\n    return None\n'
                  'def inspect():\n'
                  '    from data_sheets_schema.api_runner import PhaseRequest as LocalRequest\n'
                  '    other_api.PhaseRequest = diagnostic\n'
                  '    return LocalRequest(phase="generation", system=policy.TEXT)\n'
                  'inspect()\ninspect()\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._request_boundary_fixture_4588(d, source)
            with self.assertRaisesRegex(scan.ConfigError, "unsupported effect"):
                self._derive(root)
            off, _, off_facts = self._derive(root, sinks=False)
            self.assertTrue([row for row in off_facts["requests"]
                             if row.startswith("src/data_sheets_schema/request_boundary_4588.py:")])
            self.assertNotIn("request_policy_4588", off)


    def test_module_request_before_namespace_replacement_keeps_actual_text_trace(self):
        source = ('from data_sheets_schema import api_runner as request_api\n'
                  'from data_sheets_schema import api_runner as other_api\n'
                  'from data_sheets_schema import request_policy_4588 as policy\n'
                  'def diagnostic(**fields):\n    return None\n'
                  'original = request_api.PhaseRequest(phase="generation", system=policy.TEXT)\n'
                  'other_api.PhaseRequest = diagnostic\n')
        with tempfile.TemporaryDirectory() as d:
            root = self._request_boundary_fixture_4588(d, source)
            derived, spans, facts = self._derive(root)
            client = [row for row in facts["requests"]
                      if row.startswith("src/data_sheets_schema/request_boundary_4588.py:")]
            self.assertEqual(len(client), 1)
            self.assertIn("request_policy_4588", derived)
            self.assertEqual(self._violations(root,
                "src/data_sheets_schema/request_policy_4588.py", derived, spans),
                {("CHORUS", 1), ("VOICE", 2)})
            off, _, off_facts = self._derive(root, sinks=False)
            self.assertEqual(off_facts["requests"], facts["requests"])
            self.assertNotIn("request_policy_4588", off)


    def test_fresh_record_list_field_and_counter_keep_emitted_text_4733(self):
        """A genuine field factory allocates the list; append text and counters are emitted."""
        helper = ('from __future__ import annotations\n'
                  'from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n\n'
                  '@dataclass\nclass Stats:\n'
                  '    count: int = 0\n'
                  '    text: list = field(default_factory=list)\n\n'
                  'def describe() -> tuple[str, Stats]:\n'
                  '    stats = Stats()\n'
                  '    stats.count += 1\n'
                  '    stats.text.append(policy.SYSTEM)\n'
                  '    return f"{stats.count}: {stats.text}", stats\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(directory, '    selected, stats = effects.describe()', helper)
            derived, spans, facts = self._derive(root)
            self._assert_consumed_policy_4733(root, derived, spans, facts)

    def test_fresh_record_field_keeps_shared_nested_mutation_refusal_4733(self):
        """Fresh field allocation never detaches an object later appended into the list."""
        helper = ('from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n\n'
                  '@dataclass\nclass Stats:\n'
                  '    text: list = field(default_factory=list)\n\n'
                  'def describe(shared):\n'
                  '    stats = Stats()\n'
                  '    stats.text.append(shared)\n'
                  '    stats.text[0].append(policy.SYSTEM)\n'
                  '    return f"{stats.text}"\n')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(directory, '    selected = effects.describe([])', helper)
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn('consumed_policy_4733', off)

    def test_fresh_record_proof_rejects_custom_factory_descriptor_and_replacement_4733(self):
        """The class spelling cannot authenticate factories, post-init or replaced fields."""
        base = ('from dataclasses import dataclass, field\n'
                'from data_sheets_schema import consumed_policy_4733 as policy\n\n')
        cases = (
            ('custom_factory',
             'def factory():\n    return []\n\n@dataclass\nclass Stats:\n'
             '    text: list = field(default_factory=factory)\n', ''),
            ('post_init',
             '@dataclass\nclass Stats:\n    text: list = field(default_factory=list)\n'
             '    def __post_init__(self):\n        self.text.append(policy.SYSTEM)\n', ''),
            ('shadowed_list',
             'def list():\n    return []\n\n@dataclass\nclass Stats:\n'
             '    text: object = field(default_factory=list)\n', ''),
            ('replaced_field',
             '@dataclass\nclass Stats:\n    text: list = field(default_factory=list)\n',
             '    stats.text = make_custom()\n'),
        )
        for route, declaration, replacement in cases:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                helper = base + declaration + ('\ndef describe():\n'
                    '    stats = Stats()\n' + replacement +
                    '    stats.text.append(policy.SYSTEM)\n'
                    '    return f"{stats.text}"\n')
                root = self._consumed_helper_root_4733(directory, '    selected = effects.describe()', helper)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('consumed_policy_4733', off)

    def test_fresh_record_class_and_factory_objects_cannot_escape_identity_proof_4733(self):
        """A sole class name does not prove an unmodified constructor object."""
        prefix = ('from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n\n')
        declaration = ('@dataclass\nclass Stats:\n'
                       '    text: list = field(default_factory=list)\n\n')
        replacement = ('def replacement(self):\n    self.text = []\n\n')
        cases = (
            ('class_alias_write', declaration + replacement +
             'Other = Stats\nOther.__init__ = replacement\n', None),
            ('class_argument_escape', declaration + replacement +
             'def patch(record_type):\n    record_type.__init__ = replacement\n'
             'patch(Stats)\n', None),
            ('imported_class_write', declaration +
             'from data_sheets_schema import record_mutator_4733\n'
             'record_mutator_4733.patch()\n',
             'from data_sheets_schema.consumed_helper_4733 import Stats as Other\n'
             'def replacement(self):\n    self.text = []\n'
             'def patch():\n    Other.__init__ = replacement\n'),
            ('decorator_object_escape',
             'decorate = dataclass\n'
             'def patch(decorator):\n    decorator.__defaults__ = ()\n'
             'patch(decorate)\n' + declaration, None),
        )
        for route, setup, mutator in cases:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                helper = prefix + setup + ('\ndef describe():\n'
                    '    stats = Stats()\n'
                    '    stats.text.append(policy.SYSTEM)\n'
                    '    return f"{stats.text}"\n')
                root = self._consumed_helper_root_4733(directory, '    selected = effects.describe()', helper)
                if mutator is not None:
                    (root / 'src/data_sheets_schema/record_mutator_4733.py').write_text(mutator)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('consumed_policy_4733', off)

    def test_fresh_record_namespace_and_global_alias_cannot_hide_constructor_write_4733(self):
        """Equivalent namespace/global routes retain the same class-object identity check."""
        helper = ('from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n'
                  '@dataclass\nclass Stats:\n    text: list = field(default_factory=list)\n'
                  'from data_sheets_schema import record_mutator_4733\n'
                  'record_mutator_4733.patch()\n'
                  'def describe():\n    stats = Stats()\n'
                  '    stats.text.append(policy.SYSTEM)\n    return f"{stats.text}"\n')
        cases = (
            ('namespace_export',
             'from data_sheets_schema.consumed_helper_4733 import __dict__ as namespace\n'
             'def replacement(self):\n    self.text = []\n'
             'def patch():\n    namespace["Stats"].__init__ = replacement\n'),
            ('global_module_alias',
             'from data_sheets_schema import consumed_helper_4733 as module\n'
             'def replacement(self):\n    self.text = []\n'
             'def patch():\n    global module\n    module.Stats.__init__ = replacement\n'),
        )
        for route, mutator in cases:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                root = self._consumed_helper_root_4733(directory, '    selected = effects.describe()', helper)
                (root / 'src/data_sheets_schema/record_mutator_4733.py').write_text(mutator)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('consumed_policy_4733', off)

    def test_returned_fresh_record_cannot_hide_later_constructor_replacement_4733(self):
        """A prior returned instance exposes its actual class before the later request call."""
        helper = ('from __future__ import annotations\n'
                  'from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n'
                  '@dataclass\nclass Stats:\n    text: list = field(default_factory=list)\n'
                  'borrowed = []\n'
                  'def replacement(self):\n    self.text = borrowed\n'
                  'def patch_record(record):\n'
                  '    record_type = type(record)\n'
                  '    record_type.__init__ = replacement\n'
                  'def describe():\n    stats = Stats()\n'
                  '    stats.text.append(policy.SYSTEM)\n'
                  '    return f"{stats.text}", stats\n')
        routes = (
            ('type', '    record_type = type(prior)\n'
                     '    record_type.__init__ = replacement\n'),
            ('class_attribute', '    record_type = prior.__class__\n'
                                '    record_type.__init__ = replacement\n'),
            ('receiving_helper', '    effects.patch_record(prior)\n'),
        )
        for route, mutation in routes:
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                invocation = ('    def replacement(self):\n        self.text = parts\n'
                              '    earlier, prior = effects.describe()\n' + mutation +
                              '    selected, stats = effects.describe()')
                root = self._consumed_helper_root_4733(directory, invocation, helper)
                with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                    self._derive(root)
                off, _, _ = self._derive(root, sinks=False)
                self.assertNotIn('consumed_policy_4733', off)

    def test_repeated_record_returns_with_field_reads_retain_emitted_text_4733(self):
        """Repeated calls and tuple unpacking alone do not manufacture a reflection escape."""
        helper = ('from __future__ import annotations\n'
                  'from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n'
                  '@dataclass\nclass Stats:\n    count: int = 0\n'
                  '    text: list = field(default_factory=list)\n'
                  'def describe() -> tuple[str, Stats]:\n'
                  '    stats = Stats()\n    stats.count += 1\n'
                  '    stats.text.append(policy.SYSTEM)\n'
                  '    return f"{stats.count}: {stats.text}", stats\n')
        invocation = ('    earlier, prior = effects.describe()\n'
                      '    selected, stats = effects.describe()\n'
                      '    selected = f"{earlier} {selected} {prior.count} {stats.count}"')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(directory, invocation, helper)
            derived, spans, facts = self._derive(root)
            self._assert_consumed_policy_4733(root, derived, spans, facts)

    def test_record_origin_recursion_refuses_growing_tuple_context_4733(self):
        """A finite actual call still has a recursive static origin equation to refuse."""
        helper = ('from __future__ import annotations\n'
                  'from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n'
                  '@dataclass\nclass Stats:\n    text: list = field(default_factory=list)\n'
                  'def describe():\n    stats = Stats()\n'
                  '    stats.text.append(policy.SYSTEM)\n'
                  '    return f"{stats.text}", stats\n'
                  'def wrap(record, again=False):\n'
                  '    return wrap((record,), False) if again else record\n')
        invocation = ('    earlier, prior = effects.describe()\n'
                      '    wrapped = effects.wrap(prior, True)\n'
                      '    selected, stats = effects.describe()')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(directory, invocation, helper)
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn('consumed_policy_4733', off)

    def test_local_imported_record_producer_overrides_same_module_function_4733(self):
        """Caller discovery must see the imported producer before authenticating its body."""
        helper = ('from __future__ import annotations\n'
                  'from dataclasses import dataclass, field\n'
                  'from data_sheets_schema import consumed_policy_4733 as policy\n'
                  '@dataclass\nclass Stats:\n    text: list = field(default_factory=list)\n'
                  'def describe():\n    stats = Stats()\n'
                  '    stats.text.append(policy.SYSTEM)\n'
                  '    return f"{stats.text}", stats\n')
        imports = 'def describe():\n    return "unrelated local function"\n'
        invocation = ('    from data_sheets_schema.consumed_helper_4733 import describe\n'
                      '    def replacement(self):\n        self.text = parts\n'
                      '    earlier, prior = describe()\n'
                      '    record_type = type(prior)\n'
                      '    record_type.__init__ = replacement\n'
                      '    selected, stats = effects.describe()')
        with tempfile.TemporaryDirectory() as directory:
            root = self._consumed_helper_root_4733(directory, invocation, helper, imports)
            with self.assertRaisesRegex(scan.ConfigError, 'unsupported effect'):
                self._derive(root)
            off, _, _ = self._derive(root, sinks=False)
            self.assertNotIn('consumed_policy_4733', off)


























#: A runner small enough to make monolithic: one phase, a model-call
#: wrapper, a plan, the guards the derivations read (#4057, #4058).
SYNTHETIC_RUNNER = '''
CONDITION_PROMPTS = {"generic": "src/download/prompts/g.md", "generic_v2": "src/download/prompts/g2.md"}
RECEIPT_CONDITIONS = ("generic_v2",)
PHASES = ("full",)
DERIVED_PHASES = ()
CORE_DERIVED = False
AGENTIC_RUNTIMES = ("Claude Code",)


class RunSpec:
    def __post_init__(self):
        self.render_version = 7 if self.is_agentic else 8
        if self.render_version not in (1, 2, 3, 4, 5, 6, 7, 8, 19, 20):
            raise ValueError("unsupported")


def build_phase(spec, phase, *, carry):
    if spec.render_version >= 20 and phase == "audit":
        raise ValueError("batch")
    return SCHEMA_SEND


def plan(spec):
    return {"conditional_calls": PLANNED}


def _send(client, **kw):
    return client.messages.create(**kw)


def _call(spec, phase, client):
    return _send(client)


def execute(spec, *, dry_run=False):
    if spec.render_version in (19, 20):
        raise ValueError("continuation")
    return _execute(spec)


def _execute(spec):
    for ph in PHASES:
        _call(spec, ph, None)
'''


def _synthetic_root(d: Path, *, schema: str = "'data_sheets_schema_all.yaml'", planned: str = "[]",
                    extra: str = "", phases: str = '("full",)', heads: int = 1) -> Path:
    runner = SYNTHETIC_RUNNER.replace("SCHEMA_SEND", schema).replace("PLANNED", planned) \
        .replace('PHASES = ("full",)', f"PHASES = {phases}") + extra
    _write(d / scan.RUNNER, runner)
    _write(d / scan.CLI_API, 'import click\nARMS = {"baseline": ("B", "m", "{p}_preprocessed.txt", '
                             '"# Source manifest: x"), "other": ("O", "m2", "{p}_other.txt", "# Source manifest: y")}\n'
                             '@click.option("--arm", default="baseline")\ndef run(condition=None):\n'
                             '    if condition is None:\n        condition = "generic"\n')
    _write(d / scan.AGENTIC_RUNTIME, 'SCHEMAS = (Path("s_all.yaml"),)\n')
    _write(d / scan.PLAYBOOK, "".join(f"## Phase {i} - step\n" for i in range(1, heads + 1)))
    for name in ("g.md", "g2.md"):
        _write(d / "src/download/prompts" / name, "# header\n## Prompt body\nDescribe the dataset.\n")
    return d


class TestOptionalFollowupDerivation(unittest.TestCase):
    """#4263: optional turns come from bound helper calls, never a allowlist."""

    HELPER = "src/data_sheets_schema/optional_turn.py"
    CALLER = ("\n    if spec.restore_version:\n"
              "        from data_sheets_schema.optional_turn import run as restore\n"
              "        restore(spec, None)\n")
    BODY = ("PHASE = 'restore_full'\n"
            "def run(spec, client):\n"
            "    from data_sheets_schema import api_runner as api\n"
            "    return api._call(spec, PHASE, client)\n")

    def root(self, d):
        root = _synthetic_root(Path(d).resolve(),
                               planned="(['restore_full: optional restoration'] if spec.restore_version else [])")
        text = (root / scan.RUNNER).read_text()
        text = text.replace("class RunSpec:\n", "class RunSpec:\n    restore_version: int = 0\n")
        text = text.replace('            raise ValueError("unsupported")',
                            '            raise ValueError("unsupported")\n'
                            '        if type(self.restore_version) is not int or self.restore_version not in (0, 1):\n'
                            '            raise ValueError("version")\n'
                            '        if self.restore_version and (self.is_agentic or self.render_version != 8):\n'
                            '            raise ValueError("renderer")')
        _write(root / scan.RUNNER, text + self.CALLER)
        _write(root / self.HELPER, self.BODY)
        return root

    def derive(self, root):
        consts = scan._module_constants(root / scan.RUNNER)
        return scan.derive_followups(scan._tree(root / scan.RUNNER), list(consts["PHASES"]), consts, root=root)

    def test_optional_turn_is_not_a_default_monolithic_call(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.root(d)
            facts = {"conditions": scan.condition_table(root), "controllers": {}, "legacy_scripts": []}
            meaning = scan.api_meaning(root, facts)
        self.assertEqual(set(meaning["followup_turns"]), {"restore_full"})
        for row in meaning["conditions"].values():
            self.assertEqual(row["shape"], "MONOLITHIC")
            self.assertEqual(row["followup_turns"], [])
            self.assertEqual(row["optional_followup_turns"], ["restore_full"])
        self.assertTrue(any("restore_version" in v and "default 0 disables" in v for v in meaning["verdict"]))

    def test_renamed_axis_module_alias_phase_and_renderer_are_derived(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.root(d)
            text = (root / scan.RUNNER).read_text().replace("restore_version", "receipt_version")
            text = text.replace("restore_full", "receipt_completion").replace("self.render_version != 8", "self.render_version != 7")
            text = text.replace("from data_sheets_schema.optional_turn import run as restore",
                                "from data_sheets_schema import optional_turn as helper")
            text = text.replace("restore(spec, None)", "helper.run(spec, None)")
            _write(root / scan.RUNNER, text)
            _write(root / self.HELPER, self.BODY.replace("restore_full", "receipt_completion").replace("api_runner as api", "api_runner as renamed").replace("api._call", "renamed._call"))
            turns = self.derive(root)
        self.assertEqual(set(turns), {"receipt_completion"})
        self.assertEqual(turns["receipt_completion"]["selection"]["field"], "receipt_version")
        self.assertEqual(turns["receipt_completion"]["selection"]["renderers"], [7])

    CONDITION_BLOCK = ('        if self.restore_version:\n'
                       '            if self.condition not in ALLOWED_TURNS:\n'
                       '                raise ValueError("condition")\n')

    def restricted(self, root, *, value="frozenset({'generic_v2'})", block=None):
        text = (root / scan.RUNNER).read_text()
        text = f"ALLOWED_TURNS = {value}\n" + text
        text = text.replace('            raise ValueError("renderer")\n',
                            '            raise ValueError("renderer")\n' + (block or self.CONDITION_BLOCK))
        _write(root / scan.RUNNER, text)
        return text

    def test_optional_condition_scope_is_derived_and_does_not_change_default_shape(self):
        for value in ("frozenset({'generic_v2'})", "{'generic_v2'}", "('generic_v2',)",
                      "['generic_v2']", "set(('generic_v2',))", "tuple(['generic_v2'])"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                self.restricted(root, value=value)
                facts = {"conditions": scan.condition_table(root), "controllers": {}, "legacy_scripts": []}
                meaning = scan.api_meaning(root, facts)
                turn = meaning["followup_turns"]["restore_full"]
                self.assertEqual(turn["conditions"], ["generic_v2"])
                self.assertEqual(turn["selection"]["conditions"], ["generic_v2"])
                self.assertIn("api_runner.py:1", turn["selection"]["evidence"])
                self.assertEqual(meaning["conditions"]["generic"]["optional_followup_turns"], [])
                self.assertEqual(meaning["conditions"]["generic_v2"]["optional_followup_turns"], ["restore_full"])
                for row in meaning["conditions"].values():
                    self.assertEqual(row["followup_turns"], [])
                    self.assertEqual(row["shape"], "MONOLITHIC")

    def test_renamed_set_and_changed_members_are_read_from_the_guard(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.root(d)
            text = self.restricted(root, value="('generic',)").replace("ALLOWED_TURNS", "MY_SCOPE")
            _write(root / scan.RUNNER, text)
            self.assertEqual(self.derive(root)["restore_full"]["conditions"], ["generic"])

    def test_multiple_direct_condition_refusals_intersect(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.root(d)
            block = self.CONDITION_BLOCK + self.CONDITION_BLOCK.replace("ALLOWED_TURNS", "OTHER_SCOPE")
            text = self.restricted(root, value="('generic', 'generic_v2')", block=block)
            _write(root / scan.RUNNER, "OTHER_SCOPE = ('generic',)\n" + text)
            self.assertEqual(self.derive(root)["restore_full"]["conditions"], ["generic"])

    def test_unknown_or_wrong_polarity_condition_restrictions_fail_closed(self):
        blocks = [
            self.CONDITION_BLOCK.replace("if self.restore_version:", "if not self.restore_version:"),
            self.CONDITION_BLOCK.replace("if self.restore_version:", "if self.restore_version and extra:"),
            self.CONDITION_BLOCK.replace("if self.restore_version:", "if self.restore_version:\n            pass\n        else:"),
            self.CONDITION_BLOCK.replace("self.condition not in ALLOWED_TURNS", "self.condition in ALLOWED_TURNS"),
            self.CONDITION_BLOCK.replace("self.condition not in ALLOWED_TURNS", "self.condition != 'generic_v2'"),
            self.CONDITION_BLOCK.replace("self.condition not in ALLOWED_TURNS", "self.condition not in ALLOWED_TURNS and extra"),
            self.CONDITION_BLOCK.replace("self.condition not in ALLOWED_TURNS", "check(self.condition)"),
            self.CONDITION_BLOCK.replace("self.condition not in ALLOWED_TURNS", "getattr(self, 'condition') not in ALLOWED_TURNS"),
            self.CONDITION_BLOCK.replace('raise ValueError("condition")', 'check(self)'),
            self.CONDITION_BLOCK.replace('                raise ValueError("condition")',
                                        '                if extra:\n                    raise ValueError("condition")'),
            '        if extra:\n' + ''.join('    ' + line + '\n' for line in self.CONDITION_BLOCK.splitlines()),
            '        if self.condition not in ALLOWED_TURNS:\n'
            '            if self.restore_version:\n                raise ValueError("condition")\n',
        ]
        for block in blocks:
            with self.subTest(block=block), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                self.restricted(root, block=block)
                with self.assertRaisesRegex(scan.ConfigError, "not derived.*condition restriction"):
                    self.derive(root)

    def test_ambiguous_condition_constants_and_values_fail_closed(self):
        values = ["()", "(1,)", "('generic_v2', 1)", "choose()", "OTHER_SCOPE",
                  "frozenset({'generic_v2'}, unexpected=True)", "[c for c in ['generic_v2']]", "(' ',)"]
        for value in values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                self.restricted(root, value=value)
                with self.assertRaisesRegex(scan.ConfigError, "not derived.*condition restriction"):
                    self.derive(root)

    def test_shadowed_mutated_or_aliased_condition_sets_fail_closed(self):
        mutations = [
            lambda t: t + "\nALLOWED_TURNS = ('generic',)\n",
            lambda t: t + "\nif extra:\n    ALLOWED_TURNS = ('generic',)\n",
            lambda t: t + "\nALLOWED_TURNS.add('generic')\n",
            lambda t: t + "\nALIAS = ALLOWED_TURNS\nALIAS.add('generic')\n",
            lambda t: t + "\ndef change():\n    global ALLOWED_TURNS\n    ALLOWED_TURNS = ('generic',)\n",
            lambda t: t + "\ndef frozenset(value):\n    return ('generic',)\n",
            lambda t: t.replace("def __post_init__(self):", "def __post_init__(self, ALLOWED_TURNS=('generic',)):"),
            lambda t: t.replace("def __post_init__(self):", "def __post_init__(self):\n        ALLOWED_TURNS = ('generic',)"),
            lambda t: t.replace("def __post_init__(self):", "def __post_init__(self):\n        from other import ALLOWED_TURNS"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                _write(root / scan.RUNNER, mutation(self.restricted(root)))
                with self.assertRaisesRegex(scan.ConfigError, "not derived.*condition restriction"):
                    self.derive(root)

    def test_mutated_or_shadowed_spec_condition_cannot_reuse_scope(self):
        mutations = [
            lambda t: t.replace("def __post_init__(self):", "def __post_init__(self):\n        self = other"),
            lambda t: t.replace("def __post_init__(self):", "def __post_init__(self):\n        self.condition = 'generic_v2'"),
            lambda t: t.replace("restore(spec, None)", "spec.condition = 'generic'\n        restore(spec, None)"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                _write(root / scan.RUNNER, mutation(self.restricted(root)))
                with self.assertRaisesRegex(scan.ConfigError, "not derived"):
                    self.derive(root)

    def test_unconditional_rejection_before_or_after_condition_guard_fails_closed(self):
        for statement in ('raise ValueError("unconditional")', 'assert False', 'assert extra'):
            for where in ("before", "after", "initializer"):
                with self.subTest(statement=statement, where=where), tempfile.TemporaryDirectory() as d:
                    root = self.root(d)
                    block = self.CONDITION_BLOCK
                    if where == "before":
                        block = block.replace('            if self.condition',
                                              f'            {statement}\n            if self.condition')
                    elif where == "after":
                        block += f'            {statement}\n'
                    text = self.restricted(root, block=block)
                    if where == "initializer":
                        text = text.replace('    def __post_init__(self):',
                                            f'    def __post_init__(self):\n        {statement}')
                    _write(root / scan.RUNNER, text)
                    with self.assertRaisesRegex(scan.ConfigError, "not derived.*condition restriction"):
                        self.derive(root)

    def test_direct_imported_wrapper_alias_is_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.root(d)
            text = self.BODY.replace("from data_sheets_schema import api_runner as api",
                                     "from data_sheets_schema.api_runner import _call as send")
            _write(root / self.HELPER, text.replace("api._call", "send"))
            self.assertIn("restore_full", self.derive(root))

    def test_plan_gate_mutations_fail_closed(self):
        mutations = [
            ("if spec.restore_version else []", "if spec.unknown_version else []"),
            ("if spec.restore_version else []", "if spec.restore_version and spec.condition == 'generic' else []"),
            ("if spec.restore_version else []", "if not spec.restore_version else []"),
            ("if spec.restore_version else []", "if spec.condition in RECEIPT_CONDITIONS or spec.restore_version else []"),
            ("if spec.restore_version else []", "if spec.restore_version else ['other: alternative']"),
            ("restore_version: int = 0", "restore_version: int = 1"),
            ("restore_version: int = 0", "restore_version: bool = False"),
            ("type(self.restore_version) is not int or ", ""),
            ("self.restore_version not in (0, 1)", "self.restore_version not in (False, True)"),
            ("if self.restore_version and (self.is_agentic or self.render_version != 8):", "if False:"),
            ("self.render_version != 8", "self.render_version != 99"),
            ("self.render_version != 8", "self.render_version != 20"),
            ("    def __post_init__(self):", "    def __post_init__(self):\n        return"),
            ('            raise ValueError("renderer")', '            raise ValueError("renderer")\n        self.restore_version = 1'),
        ]
        for before, after in mutations:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                text = (root / scan.RUNNER).read_text()
                self.assertIn(before, text)
                _write(root / scan.RUNNER, text.replace(before, after))
                with self.assertRaisesRegex(scan.ConfigError, "not derived"):
                    self.derive(root)

    def test_runtime_guard_and_identity_mutations_fail_closed(self):
        replacements = [
            self.CALLER.replace("if spec.restore_version:", "if True:"),
            self.CALLER.replace("if spec.restore_version:", "if spec.restore_version:\n        pass\n    else:"),
            self.CALLER.replace("if spec.restore_version:", "if not spec.restore_version:"),
            self.CALLER.replace("if spec.restore_version:", "if spec.restore_version and spec.condition == 'generic':"),
            self.CALLER + self.CALLER.replace("if spec.restore_version:", "if True:"),
            self.CALLER.replace("restore(spec, None)", "restore(other_spec, None)"),
            self.CALLER.replace("restore(spec, None)", "spec = other_spec\n        restore(spec, None)"),
            self.CALLER.replace("restore(spec, None)", "spec.restore_version = 0\n        restore(spec, None)"),
            self.CALLER.replace("restore(spec, None)", "restore = other\n        restore(spec, None)"),
            self.CALLER.replace("restore(spec, None)", "def unused():\n            restore(spec, None)"),
        ]
        for replacement in replacements:
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                text = (root / scan.RUNNER).read_text()
                _write(root / scan.RUNNER, text.replace(self.CALLER, replacement))
                with self.assertRaisesRegex(scan.ConfigError, "not derived"):
                    self.derive(root)

    def test_missing_changed_unreadable_or_shadowed_helper_cannot_disappear(self):
        mutations = [
            None,
            self.BODY.replace("restore_full", "other_phase"),
            self.BODY.replace("PHASE = 'restore_full'", "PHASE = choose()"),
            self.BODY.replace("api._call(spec, PHASE, client)", "None"),
            self.BODY.replace("api._call(spec, PHASE, client)", "api._call(spec, choose(), client)"),
            self.BODY.replace("api._call(spec, PHASE, client)", "api._call(other_spec, PHASE, client)"),
            self.BODY.replace("    return api._call", "    api = other\n    return api._call"),
            self.BODY.replace("    return api._call", "    def api():\n        pass\n    return api._call"),
            self.BODY.replace("    return api._call", "    api._call = other\n    return api._call"),
            self.BODY.replace("    return api._call", "    def unused():\n        return api._call"),
            self.BODY.replace("from data_sheets_schema import api_runner as api", "from data_sheets_schema import other as api"),
            "def unrelated():\n    from data_sheets_schema import api_runner as api\n" + self.BODY.replace("    from data_sheets_schema import api_runner as api\n", ""),
        ]
        for changed in mutations:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as d:
                root = self.root(d)
                if changed is None:
                    (root / self.HELPER).unlink()
                else:
                    _write(root / self.HELPER, changed)
                with self.assertRaisesRegex(scan.ConfigError, "not derived"):
                    self.derive(root)


class TestCorrelatedFollowupDerivation(unittest.TestCase):
    """New source shapes use neutral renamed axes/phases, never an allowlist."""
    HELPER = 'src/data_sheets_schema/batch_calls.py'
    PLAN = 'src/data_sheets_schema/batch_plan.py'

    def root(self, directory):
        root = TestOptionalFollowupDerivation().root(directory)
        path = root / scan.RUNNER
        text = path.read_text()
        text = text.replace('"generic_v2": "src/download/prompts/g2.md"',
                            '"generic_v2": "src/download/prompts/g2.md", "generic_v3": "src/download/prompts/g3.md"')
        text = text.replace('RECEIPT_CONDITIONS = ("generic_v2",)', 'RECEIPT_CONDITIONS = ("generic_v2", "generic_v3")')
        text = text.replace('PHASES = ("full",)', 'PHASES = ("full", "audit", "report")')
        text = text.replace('restore_version: int = 0', 'restore_version: int = 0\n    flow_version: int = 0\n    guide_version: int = 0')
        text = text.replace('(1, 2, 3, 4, 5, 6, 7, 8, 19, 20)', '(1, 2, 3, 4, 5, 6, 7, 8, 9, 19, 20)')
        text = text.replace('self.restore_version not in (0, 1)', 'self.restore_version not in (0, 1, 2)')
        text = text.replace('if self.restore_version and (self.is_agentic', 'if self.restore_version == 1 and (self.is_agentic')
        needle='            raise ValueError("renderer")'
        guards='''
        if type(self.flow_version) is not int or self.flow_version not in (0, 1):
            raise ValueError('flow domain')
        if type(self.guide_version) is not int or self.guide_version not in (0, 1, 2):
            raise ValueError('guide domain')
        if self.condition == 'generic_v3' and self.flow_version != 1:
            raise ValueError('condition requires flow')
        if self.render_version == 9 and self.flow_version != 1:
            raise ValueError('renderer requires flow')
        if self.flow_version:
            if self.is_agentic or self.render_version != 9:
                raise ValueError('flow API renderer')
            if self.condition != 'generic_v3':
                raise ValueError('flow condition')
            if self.guide_version != 2 or self.restore_version != 2:
                raise ValueError('flow companions')
        if self.restore_version == 2 and self.flow_version != 1:
            raise ValueError('restore companion')
        if self.guide_version == 2 and self.flow_version != 1:
            raise ValueError('guide companion')
        if self.guide_version == 1 and (self.is_agentic or self.render_version != 8):
            raise ValueError('guide API renderer')
        if self.restore_version:
            if self.condition not in RECEIPT_CONDITIONS:
                raise ValueError('receipt condition')
'''
        text=text.replace(needle,needle+guards)
        text=text.replace('def plan(spec):\n', 'def plan(spec):\n    if spec.flow_version:\n        from data_sheets_schema.batch_plan import plan as selected_plan\n        return selected_plan(spec)\n')
        text=text.replace('    for ph in PHASES:\n        _call(spec, ph, None)', '''    for ph in PHASES:
        if ph == 'audit':
            if spec.flow_version:
                from data_sheets_schema.batch_calls import run as batch
                batch(spec, None)
            else:
                ordinary(spec, ph, None)
        else:
            ordinary(spec, ph, None)''')
        text += '\ndef ordinary(spec, phase, client):\n    return _call(spec, phase, client)\n'
        _write(path,text)
        _write(root/'src/download/prompts/g3.md','# header\n## Prompt body\nNeutral selected condition.\n')
        _write(root/self.HELPER, '''WORKER = 'sample_worker'
OMISSION = 'sample_omission'
INTEGRATION = 'sample_integration'
def run(spec, client):
    from data_sheets_schema import api_runner as api
    if stage['phase'] == WORKER:
        return api._call(spec, WORKER, client)
    elif stage['phase'] == OMISSION:
        return api._call(spec, OMISSION, client)
    elif stage['phase'] == INTEGRATION:
        return api._call(spec, INTEGRATION, client)
    else:
        raise ValueError('unknown stage')
''')
        _write(root/self.PLAN, '''def plan(spec):
    from data_sheets_schema.batch_calls import WORKER, OMISSION, INTEGRATION
    from data_sheets_schema.optional_turn import PHASE
    return {'conditional_calls': [f'{PHASE}: completion', f'{WORKER}: each actual worker',
                                  f'{OMISSION}: one source pass', f'{INTEGRATION}: one integration']}
''')
        return root

    def derive(self, root):
        consts=scan._module_constants(root/scan.RUNNER)
        return scan.derive_followups(scan._tree(root/scan.RUNNER), list(consts['PHASES']),consts,root=root)

    def test_correlated_cases_and_replacement_match_actual_call_sites(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.root(directory); turns=self.derive(root)
            receipt=turns['restore_full']['selection']
            actual={(row['values']['restore_version'],row['values']['flow_version'],tuple(row['renderers']),tuple(row['conditions']))
                    for row in receipt['cases']}
            self.assertEqual(actual,{(1,0,(8,),('generic_v2',)),(2,1,(9,),('generic_v3',))})
            for phase in ('sample_worker','sample_omission','sample_integration'):
                row=turns[phase]
                self.assertEqual(row['selection']['conditions'],['generic_v3'])
                self.assertEqual(row['via'][0]['replacement']['phase'],'audit')
                self.assertTrue(row['calls'][0].startswith(self.HELPER+':'))
                self.assertTrue(row['delegated_plan']['evidence'][-1].startswith(self.PLAN+':'))
            meaning=scan.api_meaning(root,{'conditions':scan.condition_table(root),'controllers':{},'legacy_scripts':[]})
            self.assertEqual(meaning['conditions']['generic']['model_calls_minimum'],3)
            self.assertIsNone(meaning['conditions']['generic_v3']['model_calls_minimum'])
            selected=meaning['conditions']['generic_v3']['selected_procedure']
            self.assertEqual(selected['ordinary_model_phases'],['full','report'])
            self.assertEqual(set(selected['replaced_model_phases']['audit']),{'sample_worker','sample_omission','sample_integration'})
            self.assertIn('record-dependent',selected['count_basis'])
            rendered=scan._selection_text(receipt)
            self.assertIn(' OR ',rendered)
            self.assertIn('restore_version=2',rendered)

    def test_correlated_selector_mutations_fail_closed_or_change_actual_cases(self):
        mutations=[
            ('self.restore_version == 2 and self.flow_version != 1','self.restore_version == 2 and self.flow_version != 0'),
            ('if self.is_agentic or self.render_version != 9:', 'if self.render_version != 9:'),
            ('self.restore_version not in (0, 1, 2)','self.restore_version not in (0, 1, 2, 3)'),
            ('type(self.flow_version) is not int or ',''),
            ('flow_version: int = 0','flow_version: int = 1'),
            ("if self.condition == 'generic_v3' and self.flow_version != 1:", 'if False:'),
            ("if self.condition == 'generic_v3' and self.flow_version != 1:", "self.render_version = 8\n        if self.condition == 'generic_v3' and self.flow_version != 1:"),
            ('if self.render_version == 9 and self.flow_version != 1:', 'if False:'),
            ('self.guide_version != 2 or self.restore_version != 2','self.guide_version != 1 or self.restore_version != 2'),
            ("if spec.flow_version:\n                from", "if not spec.flow_version:\n                from"),
            ('batch(spec, None)','batch(other, None)'),
            ('batch(spec, None)','spec.flow_version = 0\n                batch(spec, None)'),
            ('batch(spec, None)','spec.restore_version = 1\n                batch(spec, None)'),
            ('batch(spec, None)',"spec.runtime = 'foreign'\n                batch(spec, None)"),
        ]
        for before,after in mutations:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as directory:
                root=self.root(directory);path=root/scan.RUNNER
                text=path.read_text();self.assertIn(before,text);_write(path,text.replace(before,after))
                with self.assertRaisesRegex(scan.ConfigError,'not derived'):
                    self.derive(root)

    def test_early_plan_and_wrapper_mutations_cannot_hide_calls(self):
        mutations=[
            (scan.RUNNER,'return selected_plan(spec)','return selected_plan(other)'),
            (scan.RUNNER,'return selected_plan(spec)','return dict(selected_plan(spec))'),
            (scan.RUNNER,'return selected_plan(spec)',"selected_plan = other\n        return selected_plan(spec)"),
            (scan.RUNNER,'if spec.flow_version:\n        from','if True:\n        from'),
            (self.PLAN,"f'{PHASE}: completion', ",''),
            (self.PLAN,"f'{WORKER}: each actual worker'","f'{WORKER} each actual worker'"),
            (self.PLAN,"f'{WORKER}: each actual worker'","f'{WORKER}: each actual worker', f'{WORKER}: duplicate'"),
            (self.PLAN,"return {'conditional_calls'","if spec.flow_version:\n        return {}\n    return {'conditional_calls'"),
            (self.PLAN,"return {'conditional_calls'","spec.flow_version = 0\n    return {'conditional_calls'"),
            (self.PLAN,"return {'conditional_calls'","raise ValueError('dead')\n    return {'conditional_calls'"),
            (self.HELPER,'api._call(spec, WORKER, client)',"api._call(spec, stage['phase'], client)"),
            (self.HELPER,'return api._call(spec, OMISSION, client)','return None'),
            (self.HELPER,'from data_sheets_schema import api_runner as api',"from data_sheets_schema import api_runner as api\n    WORKER = 'foreign'"),
            (self.HELPER,'return api._call(spec, WORKER, client)','return api._call(other, WORKER, client)'),
        ]
        for relative,before,after in mutations:
            with self.subTest(relative=relative,after=after), tempfile.TemporaryDirectory() as directory:
                root=self.root(directory);path=root/relative
                text=path.read_text();self.assertIn(before,text);_write(path,text.replace(before,after))
                with self.assertRaisesRegex(scan.ConfigError,'not derived'):
                    self.derive(root)


class TestSelectedTemplateDerivation(unittest.TestCase):
    """Actual adapted base text, not an exception for a renderer's name."""
    def fixture(self, directory):
        root = Path(directory)
        runner = '''def resolve_prompt(spec):
    body = prompt_body(spec.base_prompt)
    if spec.guide_version:
        from data_sheets_schema.api_playbook import adapt_template
        body = adapt_template(body, version=spec.guide_version)
    return body
'''
        _write(root / scan.RUNNER, runner)
        for rel in ('src/data_sheets_schema/api_playbook.py', 'src/data_sheets_schema/shared_generation.py'):
            _write(root / rel, (ROOT / rel).read_text())
        from data_sheets_schema.shared_generation import API_POLICY, ROUTING_API_POLICY
        for asset in (API_POLICY, ROUTING_API_POLICY):
            _write(root / asset, (ROOT / asset).read_text())
        prompt = scan.condition_table(ROOT)['prompts'][scan.condition_table(ROOT)['current']]
        body = (ROOT / prompt).read_text().split('## Prompt body', 1)[1]
        return root, body, {'cases': [{'values': {'guide_version': 2}}]}

    def test_real_adapter_matches_inert_source_derivation(self):
        from data_sheets_schema.api_playbook import adapt_template
        with tempfile.TemporaryDirectory() as directory:
            root, body, selection = self.fixture(directory)
            result, evidence = scan._selected_template(root, scan._tree(root / scan.RUNNER), selection, body)
            self.assertEqual(result, adapt_template(body, version=2))
            self.assertIn('READ FIRST', body)
            self.assertNotIn('READ FIRST', result)
            self.assertIn('.claude/agents/', body)
            self.assertNotIn('.claude/agents/', result)
            self.assertEqual(evidence['field'], 'guide_version')
            self.assertTrue(evidence['evidence'][0].startswith(scan.RUNNER + ':'))

    def test_changed_call_binding_or_template_shape_refuses(self):
        mutations = [
            (scan.RUNNER, 'body = adapt_template(body, version=spec.guide_version)', 'body = body'),
            (scan.RUNNER, 'body = adapt_template(body, version=spec.guide_version)',
             'adapt_template = foreign\n        body = adapt_template(body, version=spec.guide_version)'),
            (scan.RUNNER, 'version=spec.guide_version', 'version=1'),
            (scan.RUNNER, 'adapt_template(body,', 'adapt_template(other,'),
            ('src/data_sheets_schema/api_playbook.py', 'positions[8]:positions[9]', 'positions[0]:positions[9]'),
            ('src/data_sheets_schema/api_playbook.py', 'return (policy_text(version=version)', 'return (foreign(version=version)'),
            ('src/data_sheets_schema/api_playbook.py', 'positions.append(body.index(marker))', 'positions.append(0)'),
            ('src/data_sheets_schema/api_playbook.py', 'def adapt_template(', '@foreign\ndef adapt_template('),
            ('src/data_sheets_schema/api_playbook.py', 'def policy_identity(', 'class policy_text: pass\n\ndef policy_identity('),
            ('src/data_sheets_schema/api_playbook.py', 'if positions != sorted(positions):', 'if False:'),
            ('src/data_sheets_schema/api_playbook.py', 'return captured_assets(version=version - 1)', 'return foreign(version=version - 1)'),
        ]
        for path, before, after in mutations:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as directory:
                root, body, selection = self.fixture(directory)
                target = root / path; text = target.read_text(); self.assertIn(before, text)
                _write(target, text.replace(before, after))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    scan._selected_template(root, scan._tree(root / scan.RUNNER), selection, body)

    def test_changed_source_text_is_derived_not_hidden_by_a_version_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root, body, selection = self.fixture(directory)
            path = root / 'src/data_sheets_schema/api_playbook.py'
            # A text-only change does not alter the recognized section-selection
            # control shape; its actual bytes must be reflected in the result.
            text = path.read_text().replace('RUN VERSION LABEL:', 'RUN VERSION LABEL: inspect neutral-guide.md')
            _write(path, text)
            adapted, _ = scan._selected_template(root, scan._tree(root / scan.RUNNER), selection, body)
            self.assertIn('inspect neutral-guide.md', adapted)
            with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                scan._selected_template(root, scan._tree(root / scan.RUNNER),
                                        {'cases': [{'values': {'guide_version': 0}}]}, body)


class TestNativeSharedRouteDerivation(unittest.TestCase):
    """Native rendering is separately selected; it is never an API25 case."""
    RENDER = 'src/data_sheets_schema/native_shared_render.py'
    CONTRACT = 'src/data_sheets_schema/native_shared_contract.py'
    CLI = 'src/data_sheets_schema/cli/prompt.py'

    def fixture(self, directory):
        root = Path(directory)
        for path in (scan.RUNNER, self.RENDER, self.CONTRACT, self.CLI):
            _write(root / path, (ROOT / path).read_text())
        return root

    def derive(self, root):
        return scan.derive_native_shared_route(root, scan._tree(root / scan.RUNNER))

    def test_actual_native_route_and_api_cases_are_distinct(self):
        selected = self.derive(ROOT)
        self.assertEqual((selected['field'], selected['default'], selected['enabled_values']),
                         ('native_shared_generation_version', 0, [1]))
        self.assertEqual((selected['condition'], selected['renderer'], selected['runtime']),
                         ('generic_v10', 26, 'Claude Code (direct)'))
        self.assertEqual(selected['companion_axes'], dict.fromkeys((
            'native_source_attribution_version', 'shared_generation_version',
            'api_playbook_version', 'receipt_completion_version', 'removal_repair_version'), 0))
        self.assertIsNone(selected['model_calls_minimum'])
        self.assertIn('not established', selected['scope'])
        tree = scan._tree(ROOT / scan.RUNNER)
        consts = scan._module_constants(ROOT / scan.RUNNER)
        turns = scan.derive_followups(tree, consts['PHASES'], consts, root=ROOT)
        receipt = turns['full_receipt_completion']['selection']['cases']
        actual = {(row['values']['receipt_completion_version'], row['values']['shared_generation_version'],
                   tuple(row['renderers']), tuple(row['conditions'])) for row in receipt}
        self.assertEqual(actual, {(1, 0, (8,), ('generic_v7', 'generic_v8', 'generic_v9')),
                                 (2, 1, (25,), ('generic_v10',)),
                                 (3, 2, (27,), ('generic_v10_source_heading_routing_v1',
                                                'generic_v10_source_heading_span_v1'))})
        self.assertTrue(all(row['values'].get('native_shared_generation_version', 0) == 0
                            and 26 not in row['renderers'] and row['runtime'] == 'api'
                            for row in receipt))

    def test_guard_and_delegate_mutations_cannot_claim_native_api_admission(self):
        guard = "if getattr(spec, 'native_shared_generation_version', 0) or spec.render_version == 26:"
        mutations = [
            (scan.RUNNER, guard, guard.replace(' or ', ' and ')),
            (scan.RUNNER, guard, guard.replace(', 0)', ', 1)')),
            (scan.RUNNER, guard, guard.replace(', 0)', ', False)')),
            (scan.RUNNER, "raise ValueError('native shared generation requires its separate native execution registration')", 'pass'),
            (scan.RUNNER, "    " + guard + "\n        raise ValueError('native shared generation requires its separate native execution registration')",
             "    dispatch(spec)\n    " + guard + "\n        raise ValueError('native shared generation requires its separate native execution registration')"),
            (scan.RUNNER, 'validate_native_shared(self)', 'validate_native_shared(other)'),
            (scan.RUNNER, 'validate_native_shared(self)', 'validate_native_shared = foreign\n        validate_native_shared(self)'),
            (scan.RUNNER, 'return instruction(spec)', 'return instruction(other)'),
            (scan.RUNNER, '24, 25, 26, 27)', '24, 25, 27)'),
            (self.RENDER, "version not in (0, 1)", 'version not in (0, 1, 2)'),
            (self.RENDER, 'spec.runtime != c.RUNTIME', 'spec.runtime == c.RUNTIME'),
            (self.RENDER, "'api_playbook_version', 'receipt_completion_version',", "'api_playbook_version',"),
            (self.RENDER, 'getattr(spec, key) != 0', 'getattr(spec, key) != 1'),
            (self.RENDER, 'def validate_spec(spec):', '@foreign\ndef validate_spec(spec):'),
            (self.RENDER, 'version = getattr(spec,', "spec.runtime = 'foreign'\n    version = getattr(spec,"),
            (self.CONTRACT, 'RENDERER = 26', 'RENDERER = 25'),
            (self.CLI, 'render_version=contract.RENDERER', 'render_version=25'),
            (self.CLI, 'native_shared_generation_version=1', 'native_shared_generation_version=0'),
            (self.CLI, 'bind_runtime(spec, runtime_declaration, max_draft_checks)', 'bind_runtime(other, runtime_declaration, max_draft_checks)'),
            (self.CLI, 'bind_runtime(spec, runtime_declaration, max_draft_checks)', 'bind_runtime(spec, runtime_declaration, 1)'),
            (self.CLI, 'text = spec.instruction', 'execute(spec)\n        text = spec.instruction'),
            (self.CLI, "    raw = text.encode('utf-8')", "    execute(spec)\n    raw = text.encode('utf-8')"),
            (self.CLI, 'captured = capture(selection)', 'captured = capture(other)'),
            (self.CLI, '@prompt.command("render-native-shared")', '@prompt.command("other")'),
        ]
        for path, before, after in mutations:
            with self.subTest(path=path, after=after), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory)
                target = root / path; source = target.read_text(); self.assertIn(before, source)
                _write(target, source.replace(before, after))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)

    def test_native_disabled_api_invariant_is_guard_derived_not_name_based(self):
        # Exercise the same reciprocal reduction with synthetic renamed fields
        # and renderer values; no project or phase/version allowlist is used.
        fixture = TestCorrelatedFollowupDerivation()
        with tempfile.TemporaryDirectory() as directory:
            root = fixture.root(directory); path = root / scan.RUNNER
            source = path.read_text().replace('flow_version: int = 0',
                'flow_version: int = 0\n    separate_version: int = 0')
            source = source.replace("self.condition == 'generic_v3' and self.flow_version != 1",
                "self.condition == 'generic_v3' and self.flow_version != 1 and self.separate_version != 1")
            source = source.replace('def execute(spec, *, dry_run=False):', '''def execute(spec, *, dry_run=False):
    if getattr(spec, 'separate_version', 0) or spec.render_version == 20:
        raise ValueError('separate runtime')''')
            _write(path, source)
            actual = fixture.derive(root)['restore_full']['selection']['cases']
            self.assertEqual({tuple(row['renderers']) for row in actual}, {(8,), (9,)})
            _write(path, source.replace("getattr(spec, 'separate_version', 0) or", "getattr(spec, 'separate_version', 0) and"))
            with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                fixture.derive(root)

    def test_api_template_only_skips_a_proven_unreachable_native_delegate(self):
        tree = scan._tree(ROOT / scan.RUNNER)
        consts = scan._module_constants(ROOT / scan.RUNNER)
        turns = scan.derive_followups(tree, consts['PHASES'], consts, root=ROOT)
        selected = next(row['selection'] for row in turns.values()
                        if row.get('selection', {}).get('field') == 'shared_generation_version')
        # Match api_meaning's condition-specific adaptation. The union also
        # includes API3/source-heading conditions with a different playbook.
        selected = {**selected, 'cases': [case for case in selected['cases']
                                         if 'generic_v10' in case['conditions']]}
        self.assertTrue(selected['cases'])
        prompt = consts['CONDITION_PROMPTS']['generic_v10']
        body = (ROOT / prompt).read_text().split('## Prompt body', 1)[1]
        from data_sheets_schema.api_playbook import adapt_template
        adapted, _ = scan._selected_template(ROOT, tree, selected, body)
        self.assertEqual(adapted, adapt_template(body, version=2))
        source = (ROOT / scan.RUNNER).read_text()
        guard = "getattr(spec, 'native_shared_generation_version', 0) or spec.render_version == 26"
        for before, after in ((guard, guard.replace(' or ', ' and ')),
                              (guard, guard.replace('== 26', '== 25')),
                              ('return instruction(spec)', 'return instruction(other)')):
            with self.subTest(after=after), self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                scan._selected_template(ROOT, ast.parse(source.replace(before, after)), selected, body)

    def test_runtime_binding_presence_is_not_controller_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            row = self.derive(root)
            self.assertFalse(row['runtime_binding']['source_present'])
            self.assertIn('not established', row['runtime_binding']['basis'])
            path = root / row['runtime_binding']['path']
            _write(path, 'def bind_runtime(*args):\n    raise ValueError("unavailable")\n')
            row = self.derive(root)
            self.assertTrue(row['runtime_binding']['source_present'])
            self.assertIn('not executed', row['runtime_binding']['basis'])
            self.assertIn('not established', row['scope'])
            _write(path, 'def invalid syntax')
            with self.assertRaises(scan.ConfigError):
                self.derive(root)


class TestNativeCallerSharedSelectorProof(unittest.TestCase):
    """N2-R2: prove the caller cut without importing/running generation code."""
    RENDER = 'src/data_sheets_schema/native_shared_render.py'
    SHARED = 'src/data_sheets_schema/shared_generation.py'
    MODES = 'src/data_sheets_schema/source_heading_runtime.py'
    RECEIPTS = 'src/data_sheets_schema/receipt_completion.py'
    FINAL = ('        if not self.native_shared_generation_version:\n'
             '            from .shared_generation import select as select_shared\n'
             '            select_shared(self)')
    DIRECT = ('        from .shared_generation import select as select_shared\n'
              '        select_shared(self)')
    VALIDATE = ('        from .native_shared_render import validate_spec as validate_native_shared\n'
                '        validate_native_shared(self)')

    def fixture(self, directory):
        root = Path(directory)
        for path in (scan.RUNNER, self.RENDER, self.SHARED, self.MODES, self.RECEIPTS):
            _write(root / path, (ROOT / path).read_text())
        return root

    def derive(self, root):
        return scan._delegated_turn_selection(scan._tree(root / scan.RUNNER),
            ast.parse('spec.receipt_completion_version', mode='eval').body, root)

    def assert_api_cases(self, result, *, native):
        actual = {(row['values']['receipt_completion_version'], row['values']['shared_generation_version'],
                   tuple(row['renderers']), tuple(row['conditions'])) for row in result['cases']}
        self.assertEqual(actual, {(1, 0, (8,), ('generic_v7', 'generic_v8', 'generic_v9')),
                                 (2, 1, (25,), ('generic_v10',)),
                                 (3, 2, (27,), ('generic_v10_source_heading_routing_v1',
                                                'generic_v10_source_heading_span_v1'))})
        self.assertTrue(all(row['runtime'] == 'api' and 26 not in row['renderers'] for row in result['cases']))
        if native:
            self.assertTrue(all(row['values']['native_shared_generation_version'] == 0
                                for row in result['cases']))
        else:
            self.assertTrue(all('native_shared_generation_version' not in row['values']
                                for row in result['cases']))

    def test_real_caller_cut_preserves_all_api_receipt_tuples(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_api_cases(self.derive(self.fixture(directory)), native=True)

    def test_legacy_helper_bypass_and_direct_final_call_remain_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            source = (root / scan.RUNNER).read_text()
            self.assertIn(self.FINAL, source)
            _write(root / scan.RUNNER, source.replace(self.FINAL, self.DIRECT))
            helper = (root / self.SHARED).read_text()
            original = '    if not version:\n'
            self.assertIn(original, helper)
            helper = helper.replace(original, original +
                "        if getattr(spec, 'native_shared_generation_version', 0):\n"
                '            from .native_shared_render import validate_spec\n'
                '            validate_spec(spec)\n'
                '            return None\n', 1)
            _write(root / self.SHARED, helper)
            self.assert_api_cases(self.derive(root), native=True)

    def test_no_native_constructor_retains_direct_api_selection(self):
        # A standalone API constructor, with the actual shared selector and
        # its finite condition/domain declarations, needs no native proof.
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            source = (root / scan.RUNNER).read_text()
            tree = ast.parse(source)
            names = {'AGENTIC_RUNTIMES', 'SOURCE_HEADING_CONDITIONS',
                     'RECEIPT_CONDITIONS', 'CONDITION_PROMPTS'}
            constants = '\n'.join(ast.unparse(n) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))
            start = source.index('        if type(self.shared_generation_version)')
            end = source.index('        self._chunk_check_uses_manifest', start)
            guards = source[start:end].replace(' and self.native_shared_generation_version != 1', '')
            minimal = constants + '''
class RunSpec:
    shared_generation_version: int = 0
    api_playbook_version: int = 0
    receipt_completion_version: int = 0
    removal_repair_version: int = 0
    native_source_attribution_version: int = 0
    def __post_init__(self):
        if self.render_version not in (8, 25, 27):
            raise ValueError('unsupported renderer')
''' + guards + self.DIRECT + '''
    @property
    def is_agentic(self):
        return self.runtime in AGENTIC_RUNTIMES
def execute(spec):
    pass
'''
            self.assertNotIn('native_shared_generation_version', minimal)
            _write(root / scan.RUNNER, minimal)
            self.assert_api_cases(self.derive(root), native=False)

    def test_caller_guard_shape_order_and_binding_mutations_refuse(self):
        replacements = [
            (self.FINAL, self.FINAL.replace('if not self.', 'if self.')),
            (self.FINAL, self.FINAL.replace('if not self.native_shared_generation_version:',
                                           'if not self.native_shared_generation_version or extra:')),
            (self.FINAL, self.FINAL.replace('if not self.native_shared_generation_version:',
                                           'if self.native_shared_generation_version == 0:')),
            (self.FINAL, self.FINAL.replace('if not self.native_shared_generation_version:',
                                           'if not self.shared_generation_version:')),
            (self.FINAL, self.FINAL + '\n        else:\n            pass'),
            (self.FINAL, self.FINAL.replace('            select_shared(self)',
                                           '            foreign()\n            select_shared(self)')),
            (self.FINAL, self.FINAL.replace('select_shared(self)', 'select_shared(other)')),
            (self.FINAL, self.FINAL.replace('select_shared(self)',
                                           'select_shared = foreign\n            select_shared(self)')),
            (self.FINAL, self.FINAL + '\n' + self.FINAL),
            (self.VALIDATE, self.VALIDATE.replace('validate_native_shared(self)', 'validate_native_shared(other)')),
            (self.VALIDATE, self.VALIDATE.replace('validate_native_shared(self)',
                                               'validate_native_shared = foreign\n        validate_native_shared(self)')),
            (self.VALIDATE, '        pass'),
            (self.VALIDATE, '        if False:\n' + '\n'.join('    ' + line for line in self.VALIDATE.splitlines())),
            (self.VALIDATE, '        try:\n' + '\n'.join('    ' + line for line in self.VALIDATE.splitlines())
                 + '\n        except ValueError:\n            pass'),
            ('native_shared_generation_version: int = 0', 'native_shared_generation_version: bool = False'),
            ('native_shared_generation_version: int = 0', 'native_shared_generation_version: int = 1'),
            ('def __post_init__(self)', 'def __post_init__(other)'),
            ('    def __post_init__(self)', '    @foreign\n    def __post_init__(self)'),
            ('    def _select_profile(self)', '    def __post_init__(self):\n        pass\n\n    def _select_profile(self)'),
            ('    def _select_profile(self)', '    __post_init__ = foreign\n\n    def _select_profile(self)'),
            ('        sel = select_profile(self.manifest)',
             '        self.native_shared_generation_version = 1\n        sel = select_profile(self.manifest)'),
            ('    @staticmethod\n    def header_for_manifest', '    @foreign\n    def header_for_manifest'),
            ('        return self.runtime in AGENTIC_RUNTIMES',
             "        setattr(self, 'native_shared_generation_version', 1)\n        return self.runtime in AGENTIC_RUNTIMES"),
        ]
        for before, after in replacements:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory); source = (root / scan.RUNNER).read_text()
                self.assertIn(before, source)
                _write(root / scan.RUNNER, source.replace(before, after))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)

    def test_properties_and_receipt_adapter_cannot_invalidate_receiver_facts(self):
        mutations = [
            (scan.RUNNER, self.FINAL, '        self.evil\n' + self.FINAL),
            (scan.RUNNER, '        return self.output_root / self.method / self.label /',
             "        self.native_shared_generation_version = 1\n        return self.output_root / self.method / self.label /"),
            (self.RECEIPTS, "    value = parse_registration(spec.receipt_completion_registration.encode('utf-8'),",
             "    spec.native_shared_generation_version = 1\n    value = parse_registration(spec.receipt_completion_registration.encode('utf-8'),"),
            (self.RECEIPTS, 'def registration(spec) -> dict:', '@foreign\ndef registration(spec) -> dict:'),
        ]
        evil = ("\n    @property\n    def evil(self):\n"
                "        self.native_shared_generation_version = 1\n        return 0\n")
        for path, before, after in mutations:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory); source = (root / path).read_text()
                self.assertIn(before, source)
                source = source.replace(before, after)
                if after.startswith('        self.evil'):
                    source = source.replace('    def _select_profile(self)', evil + '\n    def _select_profile(self)')
                _write(root / path, source)
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)

    def test_native_receiver_class_cannot_replace_attribute_access(self):
        replacements = [
            ('class RunSpec:', 'class RunSpec(Foreign):'),
            ('class RunSpec:', 'class RunSpec(metaclass=Foreign):'),
            ('@dataclass\nclass RunSpec:', '@foreign\nclass RunSpec:'),
            ('from dataclasses import dataclass, field', 'from foreign import dataclass, field'),
            ('@dataclass\nclass RunSpec:', 'dataclass = foreign\n@dataclass\nclass RunSpec:'),
            ('    def _select_profile(self)',
             '    native_shared_generation_version = property(foreign)\n\n    def _select_profile(self)'),
        ]
        for name in ('__getattribute__', '__getattr__', '__setattr__', '__delattr__'):
            replacements.append(('    def _select_profile(self)',
                f'    def {name}(self, *args):\n        return foreign(self, *args)\n\n    def _select_profile(self)'))
        for before, after in replacements:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory); source = (root / scan.RUNNER).read_text()
                self.assertIn(before, source)
                _write(root / scan.RUNNER, source.replace(before, after))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory); source = (root / scan.RUNNER).read_text()
            line = 'from dataclasses import dataclass, field\n'
            self.assertIn(line, source)
            _write(root / scan.RUNNER, source.replace(line, '') + '\n' + line)
            with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                self.derive(root)

    def test_native_validator_cannot_read_an_unproved_property(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            self.assert_api_cases(self.derive(root), native=True)
            source = (root / scan.RUNNER).read_text()
            evil = ("    @property\n    def evil(self):\n"
                    "        self.receipt_completion_version = 2\n        return False\n\n")
            _write(root / scan.RUNNER, source.replace('    def _select_profile(self)',
                                                    evil + '    def _select_profile(self)'))
            native = (root / self.RENDER).read_text()
            _write(root / self.RENDER, native.replace('    return doc\n',
                "    if spec.evil != False:\n        raise ValueError('extra restriction')\n    return doc\n"))
            with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                self.derive(root)
        for field in ('native_shared_generation_version', 'receipt_completion_version', 'runtime'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory); source = (root / scan.RUNNER).read_text()
                shadow = f'    @property\n    def {field}(self):\n        return 0\n\n'
                _write(root / scan.RUNNER, source.replace('    def _select_profile(self)',
                                                        shadow + '    def _select_profile(self)'))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory); source = (root / scan.RUNNER).read_text()
            source = source.replace(self.VALIDATE + '\n', '')
            source = source.replace(self.FINAL, self.VALIDATE + '\n' + self.FINAL)
            _write(root / scan.RUNNER, source)
            with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                self.derive(root)

    def test_validated_receiver_cannot_change_or_escape_before_final_call(self):
        mutations = [
            'self = other', 'self.native_shared_generation_version = 1',
            "setattr(self, 'native_shared_generation_version', 1)",
            "delattr(self, 'native_shared_generation_version')",
            "self.__dict__['native_shared_generation_version'] = 1",
            "vars(self)['native_shared_generation_version'] = 1",
            "getattr(self, '__dict__')['native_shared_generation_version'] = 1",
            'alias = self\n        alias.native_shared_generation_version = 1',
            'foreign(self)', 'self.mutate()', 'alias = self._select_profile\n        alias()',
            'self._select_profile.__self__.native_shared_generation_version = 1',
            'foreign(self._select_profile)', 'self.foreign_mutator.__call__()',
            'alias = self.__class__\n        alias.__getattribute__ = foreign',
            'alias = type(self)\n        alias.__getattribute__ = foreign',
            'self._select_profile = foreign', 'return', "raise ValueError('stopped')",
        ]
        for statement in mutations:
            with self.subTest(statement=statement), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory); source = (root / scan.RUNNER).read_text()
                _write(root / scan.RUNNER, source.replace(self.FINAL, '        ' + statement + '\n' + self.FINAL))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)

    def test_native_zero_companion_proof_cannot_be_weakened_or_invalidated(self):
        replacements = [
            ('version not in (0, 1)', 'version not in (0, 1, 2)'),
            ("'api_playbook_version', 'receipt_completion_version',", "'api_playbook_version',"),
            ("'shared_generation_version',", ''),
            ('getattr(spec, key) != 0', 'getattr(spec, key) != 1'),
            ('    for key in (\'native_source_attribution_version\'',
             "    if False:\n        return None\n    for key in ('native_source_attribution_version'"),
        ]
        for statement in ('spec = other', 'spec.receipt_completion_version = 2',
                          "setattr(spec, 'receipt_completion_version', 2)",
                          "spec.__dict__['receipt_completion_version'] = 2",
                          "getattr(spec, '__dict__')['receipt_completion_version'] = 2",
                          "key = '__dict__'\n    getattr(spec, key)['receipt_completion_version'] = 2",
                          'alias = spec.__class__\n    alias.__getattribute__ = foreign',
                          'alias = spec.mutate\n    alias()',
                          "getattr(spec, 'foreign_mutator')()",
                          "getattr(spec, 'project')()",
                          "foreign(getattr(spec, 'project'))",
                          'alias = spec\n    alias.receipt_completion_version = 2', 'foreign(spec)'):
            replacements.append(('    return doc\n', '    ' + statement + '\n    return doc\n'))
        for before, after in replacements:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory); source = (root / self.RENDER).read_text()
                self.assertIn(before, source)
                _write(root / self.RENDER, source.replace(before, after))
                with self.assertRaisesRegex(scan.ConfigError, 'not derived'):
                    self.derive(root)


class TestNativeSharedProcedure:
    """Computed response-roster facts are distinct from runtime descriptions."""
    MODULES = ('native_shared_stage', 'native_shared_receipts', 'typed_audit',
               'audit_omissions', 'native_shared_render')

    @staticmethod
    def fixture(root):
        for name in TestNativeSharedProcedure.MODULES:
            relative = 'src/data_sheets_schema/' + name + '.py'
            _write(root / relative, (ROOT / relative).read_text())
        return root

    def test_actual_roster_has_unknown_observed_and_model_counts(self):
        row = scan.derive_native_shared_procedure(ROOT)
        assert [stage['kind'] for stage in row['stages']] == ['receipt', 'worker', 'omission', 'integration']
        assert [stage['cardinality'] for stage in row['stages']] == [
            'R = 0 or 1', 'W, unknown until the original record is partitioned', '1', '1']
        assert row['protocol_responses'] == {'formula': 'R + W + 2', 'minimum': None, 'actual_count': None,
            'unit': 'required response-bearing stage roster, not model calls or observed answers'}
        assert row['model_calls_minimum'] is None
        assert 'every worker' in row['stages'][1]['requirement']
        assert 'negative/redundant' in row['stages'][2]['requirement']
        assert row['helper_kind_count'] == 17
        assert row['helper_commands'] == ['chunk_check', 'source_scope', 'full_schema', 'full_terms',
            'phase1_receipts', 'advance', 'derive_core', 'core_schema', 'pair', 'original_source_inventory',
            'final_source_inventory', 'draft', 'audit_evidence', 'final_evidence', 'derive_final_core',
            'final_scope', 'recorder']
        assert 'no observed execution' in row['basis']
        assert len(row['evidence']) == 6
        assert all((ROOT / e.rsplit(':', 1)[0]).is_file() for e in row['evidence'])
        assert row['typed_worker_schema_projection']['excluded_keys'] == ['classes', 'slots']
        assert 'not equality' in row['typed_worker_schema_projection']['scope']
        assert any('exposures differ' in note['description'] for note in row['procedure_notes'])

    def test_exact_s7_schema_projection_and_mutations(self, tmp_path):
        root = self.fixture(tmp_path / 'valid')
        assert scan.derive_native_shared_procedure(root)['typed_worker_schema_projection']['excluded_keys'] == ['classes', 'slots']
        mutations = (
            ('if k not in ("classes", "slots")', 'if k not in ("classes", "slots", "enums")'),
            ('if k not in ("classes", "slots")', 'if k in ("classes", "slots")'),
            ('prepared.request()["payload"]["schema"].items()', 'foreign.request()["payload"]["schema"].items()'),
            ('{k: v for k, v in prepared.request()["payload"]["schema"].items()\n                   if k not in ("classes", "slots")}',
             'prepared.request()["payload"]["schema"]'),
        )
        for index, (before, after) in enumerate(mutations):
            changed = self.fixture(tmp_path / str(index))
            target = changed / 'src/data_sheets_schema/typed_audit.py'
            raw = target.read_text()
            assert raw.count(before) == 1, before
            target.write_text(raw.replace(before, after))
            with unittest.TestCase().assertRaisesRegex(scan.ConfigError, 'not derived'):
                scan.derive_native_shared_procedure(changed)

    def test_cardinality_and_input_mutations_fail_closed(self, tmp_path):
        # Every private mutation fixture is retained below pytest's basetemp.
        cases = [
            ('native_shared_stage', 'if requested:', 'if not requested:'),
            ('native_shared_stage', "kind='receipt', target_id='receipt'", "kind='worker', target_id='receipt'"),
            ('native_shared_stage', 'self.p, None, self.catalogs)', 'self.p, b"answer", self.catalogs)'),
            ('native_shared_stage', "nr._prepare(self.s, self.e, self.p, self.catalogs)['requested_paths']",
             "foreign(self.s, self.e, self.p)['requested_paths']"),
            ('native_shared_stage', "for worker in self.packet['plan']['workers']]",
             "for worker in self.packet['plan']['workers'][:1]]"),
            ('native_shared_stage', "for worker in self.packet['plan']['workers']]",
             "for worker in self.packet['plan']['workers'] if worker['id'] == 'worker_0001']"),
            ('native_shared_stage', "roster += [('omission', 'omission'), ('integration', 'integration')]",
             "roster += [('integration', 'integration'), ('omission', 'omission')]"),
            ('native_shared_stage', "roster += [('omission', 'omission'), ('integration', 'integration')]",
             "roster += [('integration', 'integration')]"),
            ('native_shared_stage', 'for kind, target in roster:', 'for kind, target in roster[:1]:'),
            ('native_shared_stage', 'for kind, target in roster:', "roster.pop()\n        for kind, target in roster:"),
            ('native_shared_stage', "raise ValueError('complete native stage roster exceeds declared submissions; no truncation')",
             'roster = roster[:1]'),
            ('native_shared_stage', 'original_full=self.p.full.raw,', 'original_full=other.raw,'),
            ('native_shared_stage', "max_workers=limits['max_workers']", 'max_workers=1'),
            ('native_shared_stage', 'from . import typed_audit as typed', 'from . import foreign as typed'),
            ('native_shared_receipts', "'requested_paths': paths", "'requested_paths': paths[:1]"),
            ('native_shared_receipts', 'paths = receipts.uncovered_receiptable_leaves(', 'paths = foreign('),
            ('typed_audit', "batches.make_plan(raw[\"original_full\"].decode(\"utf-8\")", 'batches.make_plan("{}"'),
            ('typed_audit', 'prepared = omissions._prepare(', 'prepared = foreign('),
            ('typed_audit', '"omission_request": prepared.request()', '"omission_request": {}'),
            ('audit_omissions', 'evidence.source_chunks_from_bytes(bundle, manifest)',
             'evidence.source_chunks_from_bytes(bundle, other)'),
            ('audit_omissions', 'for key, value in chunks.items()],',
             'for key, value in chunks.items() if prior.get(key) == "extracted"],'),
            ('audit_omissions', 'payload = {"policy": policy,',
             'chunks = {}\n    payload = {"policy": policy,'),
            ('native_shared_render', "result['recorder'] =", "result[spec.project] ="),
            ('native_shared_render', "result['recorder'] =", "result['draft'] ="),
        ]
        for index, (module, before, after) in enumerate(cases):
            root = self.fixture(tmp_path / str(index))
            target = root / 'src/data_sheets_schema' / (module + '.py')
            raw = target.read_text()
            assert before in raw, (module, before)
            target.write_text(raw.replace(before, after))
            with unittest.TestCase().assertRaisesRegex(scan.ConfigError, 'not derived'):
                scan.derive_native_shared_procedure(root)

    def test_helper_kinds_come_from_actual_mapping(self, tmp_path):
        root = self.fixture(tmp_path)
        target = root / 'src/data_sheets_schema/native_shared_render.py'
        target.write_text(target.read_text().replace("'chunk_check': (*cli", "'neutral_chunk_check': (*cli"))
        row = scan.derive_native_shared_procedure(root)
        assert row['helper_kind_count'] == 17
        assert row['helper_commands'][0] == 'neutral_chunk_check'
        assert 'chunk_check' not in row['helper_commands']

    def refuse_producer_mutation(self, root, module, before, after):
        self.fixture(root)
        target = root / 'src/data_sheets_schema' / (module + '.py')
        raw = target.read_text()
        assert raw.count(before) == 1, (module, before)
        target.write_text(raw.replace(before, after))
        with unittest.TestCase().assertRaisesRegex(scan.ConfigError, 'not derived'):
            scan.derive_native_shared_procedure(root)

    def test_original_receipt_paths_overwritten_witness(self, tmp_path):
        self.refuse_producer_mutation(tmp_path, 'native_shared_receipts',
            "    return {'protocol': contract.NAME, 'stage': 'receipt',",
            "    paths = []\n    return {'protocol': contract.NAME, 'stage': 'receipt',")

    def test_original_native_packet_workers_filtered_witness(self, tmp_path):
        self.refuse_producer_mutation(tmp_path, 'native_shared_stage', '        return packet\n',
            "        packet['plan']['workers'] = packet['plan']['workers'][:1]\n        return packet\n")

    def test_original_typed_producer_detached_witness(self, tmp_path):
        self.refuse_producer_mutation(tmp_path, 'typed_audit',
            'derived, _, _ = _derive(inputs, rows, project, limits, derivations=derivations, captured_assets=captured_assets, _schema_reuse=_schema_reuse)',
            'derived, _, _ = foreign(inputs, rows, project, limits, derivations=derivations, captured_assets=captured_assets, _schema_reuse=_schema_reuse)')

    def test_return_unpack_cannot_override_counted_receipt_field(self, tmp_path):
        # Exact independent #4403 witness, preserving the original literal
        # field and its otherwise unchanged local producer/use pair.
        self.refuse_producer_mutation(tmp_path, 'native_shared_receipts',
            "'schema': catalog, 'owner_classes': owners, 'requested_paths': paths,",
            "'schema': catalog, 'owner_classes': owners, 'requested_paths': paths, **{'requested_paths': []},")

    def test_return_dynamic_key_cannot_override_counted_receipt_field(self, tmp_path):
        self.refuse_producer_mutation(tmp_path, 'native_shared_receipts',
            "'schema': catalog, 'owner_classes': owners, 'requested_paths': paths,",
            "'schema': catalog, 'owner_classes': owners, 'requested_paths': paths, 'requested_' + 'paths': [],")

    def test_return_duplicate_literal_key_is_not_counted_authority(self, tmp_path):
        self.refuse_producer_mutation(tmp_path, 'native_shared_receipts',
            "'schema': catalog, 'owner_classes': owners, 'requested_paths': paths,",
            "'schema': catalog, 'owner_classes': owners, 'requested_paths': paths, 'requested_paths': [],")

    def test_counted_values_and_fixed_producer_delegates_cannot_escape(self, tmp_path):
        # Source-only witnesses for the finite local-use/return joins. No
        # mutated producer or runtime is imported or executed.
        cases = [
            ('native_shared_receipts', "    return {'protocol': contract.NAME, 'stage': 'receipt',",
             "    paths.clear()\n    return {'protocol': contract.NAME, 'stage': 'receipt',"),
            ('native_shared_receipts', "    return {'protocol': contract.NAME, 'stage': 'receipt',",
             "    alias = paths\n    return {'protocol': contract.NAME, 'stage': 'receipt',"),
            ('native_shared_stage', '        return packet\n', '        packet = foreign(packet)\n        return packet\n'),
            ('native_shared_stage', '        return packet\n', '        foreign(packet)\n        return packet\n'),
            ('native_shared_stage', '        return packet\n',
             '        if selected:\n            return foreign()\n        return packet\n'),
            ('native_shared_stage', "        roster = [('worker', worker['id']) for worker in self.packet['plan']['workers']]",
             "        self.packet['plan']['workers'].clear()\n        roster = [('worker', worker['id']) for worker in self.packet['plan']['workers']]"),
            ('typed_audit', 'project=project, limits=limits, **derived, limitations=list(LIMITATIONS)))',
             'project=project, limits=limits, **foreign(derived), limitations=list(LIMITATIONS)))'),
            ('typed_audit', '    packet = _seal(dict(kind=PACKET,',
             "    derived['plan']['workers'].clear()\n    packet = _seal(dict(kind=PACKET,"),
            ('typed_audit', '    packet = _seal(dict(kind=PACKET,',
             "    inputs['original_full'] = foreign()\n    packet = _seal(dict(kind=PACKET,"),
            ('typed_audit', 'return _derive_uncached(inputs, schema_rows, project, limits)',
             'return foreign(inputs, schema_rows, project, limits)'),
            ('typed_audit', 'return derivations._derive(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)',
             'return derivations.foreign(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)'),
            ('typed_audit', 'derived, raw, prepared = _derive(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)',
             'derived, raw, prepared = foreign(inputs, schema_rows, project, limits, captured_assets=captured_assets, _schema_reuse=_schema_reuse)'),
            ('typed_audit', "encoded = _json({'derived': derived, 'raw':",
             "encoded = _json({'derived': foreign(derived), 'raw':"),
            ('typed_audit', "return value['derived'], {name: _unblob(blob)",
             "return foreign(value['derived']), {name: _unblob(blob)"),
            ('typed_audit', '        value = json.loads(encoded)\n',
             "        encoded = foreign(encoded)\n        value = json.loads(encoded)\n"),
            ('typed_audit', '        encoded = self._rows.get(key)\n',
             '        self._rows[key] = foreign()\n        encoded = self._rows.get(key)\n'),
            ('typed_audit', '    return {"plan": plan, "omission_request": prepared.request(),',
             '    plan["workers"] = plan["workers"][:1]\n    return {"plan": plan, "omission_request": prepared.request(),'),
            ('typed_audit', '    return {"plan": plan, "omission_request": prepared.request(),',
             '    prepared = foreign(prepared)\n    return {"plan": plan, "omission_request": prepared.request(),'),
            ('typed_audit', 'def _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None, _schema_reuse=None):',
             '_derive = foreign\n\ndef _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None, _schema_reuse=None):'),
            ('typed_audit', 'def _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None, _schema_reuse=None):',
             'DerivationCache = Foreign\n\ndef _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None, _schema_reuse=None):'),
            ('audit_omissions', '    encoded = _json(payload)\n',
             '    payload["chunks"] = payload["chunks"][:1]\n    encoded = _json(payload)\n'),
            ('audit_omissions', '    return Prepared(encoded)\n',
             '    encoded = foreign(encoded)\n    return Prepared(encoded)\n'),
            ('audit_omissions', '                "payload": payload, "limitations": list(LIMITATIONS)}',
             '                "payload": foreign(payload), "limitations": list(LIMITATIONS)}'),
        ]
        assert scan.derive_native_shared_procedure(ROOT)['protocol_responses']['formula'] == 'R + W + 2'
        for index, (module, before, after) in enumerate(cases):
            self.refuse_producer_mutation(tmp_path / str(index), module, before, after)

    def test_unified_cache_store_and_product_keys_are_source_derived(self, tmp_path):
        # The same copied implementation must be admitted before each causal
        # source mutation. No cache implementation is imported or executed.
        root = self.fixture(tmp_path / 'positive')
        assert scan.derive_native_shared_procedure(root)['protocol_responses']['formula'] == 'R + W + 2'
        cases = [
            ("key = ('derive', len(identity), _sha(identity))",
             "key = ('open', len(identity), _sha(identity))"),
            ("key = ('open', len(raw_packet), _sha(raw_packet), captured_assets is not None, assets)",
             "key = ('derive', len(raw_packet), _sha(raw_packet), captured_assets is not None, assets)"),
            ("key = ('derive', len(identity), _sha(identity))",
             "key = ('derive', len(identity), 'fixed')"),
            ("key = ('open', len(raw_packet), _sha(raw_packet), captured_assets is not None, assets)",
             "key = ('open', len(raw_packet), _sha(raw_packet), captured_assets is not None, ())"),
            ('def _store(self, key, encoded):', 'def _store(self, encoded, key):'),
            ('def _store(self, key, encoded):', '@foreign\n    def _store(self, key, encoded):'),
            ('if len(encoded) > self.max_bytes:', 'if len(encoded) < self.max_bytes:'),
            ('self._bytes -= len(previous)', 'self._bytes -= 0'),
            ('self._rows[key] = encoded', 'self._rows[key] = foreign(encoded)'),
            ('self._store(key, encoded)', 'self._store(key, b"{}")'),
            ('self._store(key, encoded)', 'self._store(other, encoded)'),
            ('        encoded = self._rows.get(key)\n',
             '        self._store = foreign\n        encoded = self._rows.get(key)\n'),
            ('        self._rows, self._bytes = {}, 0\n',
             '        self._rows, self._bytes = {}, 0\n        self._store = foreign\n'),
            ('def _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None, _schema_reuse=None):',
             'DerivationCache._store = foreign\n\ndef _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None, _schema_reuse=None):'),
        ]
        for index, (before, after) in enumerate(cases):
            self.refuse_producer_mutation(tmp_path / ('unified-' + str(index)),
                                         'typed_audit', before, after)

    def test_private_omission_route_still_uses_complete_public_constructor(self, tmp_path):
        cases = [
            ('audit_omissions', '    return _prepare(record=record,', '    return foreign(record=record,'),
            ('audit_omissions', '    return _prepare(record=record, bundle=bundle, manifest=manifest, receipt=receipt,',
             '    return _prepare(record=record, bundle=other, manifest=manifest, receipt=receipt,'),
            ('audit_omissions', 'def _prepare(*, record: bytes,', '_prepare = foreign\n\ndef _prepare(*, record: bytes,'),
            ('typed_audit', '_catalog=(_schema_reuse.for_snapshot(snapshot)', '_catalog=(foreign(snapshot)'),
        ]
        for index, (module, before, after) in enumerate(cases):
            self.refuse_producer_mutation(tmp_path / str(index), module, before, after)

    def test_producer_comments_and_descriptions_do_not_change_semantic_disclosure(self, tmp_path):
        root = self.fixture(tmp_path)
        path = root / 'src/data_sheets_schema/typed_audit.py'
        path.write_text(path.read_text().replace(
            '    """Capture a new packet; no saved response or self-reported success is trusted."""',
            '    """An equivalent descriptive docstring."""\n    # A harmless source annotation.'))
        assert scan.derive_native_shared_procedure(root) == scan.derive_native_shared_procedure(ROOT)

    def test_description_is_not_an_inherited_phase_or_launch_validator(self, tmp_path):
        root = self.fixture(tmp_path)
        # No phase, attribution or execution modules in this structural fixture.
        # Their linked obligations cannot be mislabeled checked runtime facts.
        row = scan.derive_native_shared_procedure(root)
        notes = ' '.join(note['description'] for note in row['procedure_notes'])
        assert 'not scanner-verified execution' in notes
        assert 'not a rewrite count' in notes
        assert 'do not establish completion' in notes
        assert row['model_calls_minimum'] is None

    def test_four_actual_native_text_builders_are_model_facing(self):
        surfaces, _ = _discovered()
        for module in ('native_shared_render', 'native_shared_stage', 'native_shared_receipts', 'native_shared_contract'):
            relative = 'src/data_sheets_schema/' + module + '.py'
            assert surfaces.files[relative].role == 'model_facing'
            planted, _ = _plant(relative, 'NATIVE_POLICY_TEST = "Always prefer CHORUS."')
            assert any(h['match'] == 'CHORUS' and h['violation'] for h in planted), module

    def test_report_adds_selected_roster_without_native_call_count(self):
        result = _full_run()
        row = result['api_meaning']['native_shared_route']['procedure']
        assert row == scan.derive_native_shared_procedure(ROOT)
        text = scan.render_markdown(result)
        assert 'R + W + 2' in text
        assert 'Actual count and model-call count: unknown' in text
        assert '17 helper command kinds (not invocation counts)' in text
        assert 'runtime enforcement is not proved by this scanner' in text
        assert 'API phase construction: refused' in text


class TestApiMeaning(unittest.TestCase):
    """The "api" section agrees with what the runtime does (#4022, #4025,
    #4055, #4057, #4058)."""

    @classmethod
    def setUpClass(cls):
        cls.meaning = _meaning()
        cls.cond = _discovered()[1]["conditions"]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.bundle = _write(Path(cls.tmp.name) / "X_preprocessed.txt", "hello\n")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _cli_spec(self, project="SOMEDATASET", condition=None, **kw):
        from data_sheets_schema.cli import api as cli_api
        return cli_api._spec(project, "baseline", "2026-09-30_probe", condition, bundle=str(self.bundle),
                             manifest=None, **kw)

    def _spec_at(self, renderer: int):
        from data_sheets_schema import api_runner
        base = self._cli_spec()
        return api_runner.RunSpec(project=base.project, arm=base.arm, method=base.method, bundle=base.bundle,
                                  label=base.label, condition=self.cond["default"], manifest=None,
                                  render_version=renderer)

    def test_the_cli_default_condition_is_what_the_cli_runs(self):
        """The GitHub assistant's condition is the one its `d4d api run`
        names, or the CLI default when it names none, in full (#4057)."""
        spec = self._cli_spec()
        self.assertEqual(spec.condition, self.cond["default"])
        self.assertIn(self.cond["default"], self.cond["live"])
        gh = self.meaning["github_assistant"]
        workflow = (ROOT / ".github/workflows/d4d-agent.yml").read_text(encoding="utf-8")
        block = re.search(r"d4d api run(?:[^\n]*\\\n)*[^\n]*", workflow).group(0).replace("\\\n", " ")
        # any spelling of --condition, so a non-literal one cannot pass as
        # "no --condition" here either (#4092)
        passed = re.search(r"--condition\b", block)
        named = re.search(r"--condition(?:=|\s+)['\"]?([\w.-]+)['\"]?(?:\s|$)", block)
        self.assertEqual(bool(passed), bool(named), "a --condition the oracle cannot read: update this test")
        expected = named.group(1) if named else spec.condition
        self.assertEqual(gh["condition_name"], expected)
        self.assertEqual(gh["condition"], expected if named else f"{spec.condition} (CLI default; no --condition)")
        labelled = [c for c, v in self.meaning["conditions"].items() if "GitHub assistant" in v["role"]]
        self.assertEqual(labelled, [expected])

    def test_the_github_assistant_condition_follows_the_workflow(self):
        """A workflow that passes --condition runs that condition, not the
        CLI default (#4016, #4057)."""
        text = (ROOT / ".github/workflows/d4d-agent.yml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d) / ".github/workflows/d4d-agent.yml",
                   text.replace("d4d api run ", f"d4d api run --condition {self.cond['current']} ", 1))
            gh = scan.github_assistant_run(Path(d), self.cond)
        self.assertEqual((gh["condition_name"], gh["condition_basis"], gh["condition"]),
                         (self.cond["current"], "--condition", self.cond["current"]))

    def test_a_condition_the_workflow_chooses_when_it_runs_is_not_derived(self):
        """A --condition that is not a literal (an expression, a variable)
        is chosen when the workflow runs: "not derived", never reported as
        the CLI default with "no --condition" (#4092). Every literal
        spelling, also one continued onto the next line, is read."""
        text = (ROOT / ".github/workflows/d4d-agent.yml").read_text(encoding="utf-8")
        current = self.cond["current"]

        def run_with(spelling):
            with tempfile.TemporaryDirectory() as d:
                _write(Path(d) / ".github/workflows/d4d-agent.yml",
                       text.replace("d4d api run ", f"d4d api run {spelling} ", 1))
                return scan.github_assistant_run(Path(d), self.cond)

        for spelling in ('--condition "${{ inputs.condition }}"', "--condition=$CONDITION",
                         '--condition "$CONDITION"', "--condition ${CONDITION}", "--condition"):
            with self.subTest(spelling=spelling), \
                    self.assertRaisesRegex(scan.ConfigError, "not derived.*not a literal condition name"):
                run_with(spelling)
        for spelling in (f"--condition {current}", f"--condition={current}", f"--condition '{current}'",
                         f'--condition "{current}"', f"--condition \\\n            {current}"):
            with self.subTest(spelling=spelling):
                gh = run_with(spelling)
                self.assertEqual((gh["condition_name"], gh["condition_basis"]), (current, "--condition"))
        with self.assertRaisesRegex(scan.ConfigError, "not derived"):
            run_with(f"--condition {current} --condition generic")

    def test_the_default_renderers_are_what_the_runtime_uses(self):
        self.assertEqual(self._cli_spec().render_version, self.meaning["default_renderer"]["api"])
        agentic = sorted(self.cond["agentic_runtimes"])[0]
        self.assertEqual(self._cli_spec(runtime=agentic).render_version,
                         self.meaning["default_renderer"]["agentic"])

    def test_the_audit_floor_is_where_build_phase_refuses_the_audit(self):
        from data_sheets_schema import api_runner
        floor = self.meaning["agentic_audit_from_renderer"]
        refused = {}
        for n in (floor - 1, floor):
            spec = self._spec_at(n)
            try:
                api_runner.build_phase(spec, "audit", carry={})
                refused[n] = False
            except Exception as exc:                # noqa: BLE001 — any other failure is not the refusal
                refused[n] = "batch-context" in str(exc)
        self.assertEqual(refused, {floor - 1: False, floor: True})

    def test_execute_refuses_what_the_scan_reports(self):
        """api_runner.execute refuses the reported renderers before it runs,
        and gets past the check at the highest renderer it does not refuse
        (#4055). Nothing here reaches a provider: the run stops at the lock."""
        from data_sheets_schema import api_runner
        ex = self.meaning["audit_continuations"]["execute_refuses"]
        self.assertEqual(ex["refused"], [19, 20, 21, 22, 23, 24, 26])
        for n in (19, 20, 21, 22, 23, 24):
            with self.subTest(renderer=n), self.assertRaisesRegex(ValueError, "separately registered"):
                api_runner.execute(self._spec_at(n))
        from types import SimpleNamespace
        with self.assertRaisesRegex(ValueError, 'separate native execution registration'):
            api_runner.execute(SimpleNamespace(render_version=26, native_shared_generation_version=0))
        selected = {r for procedure in self.meaning.get('selected_procedures', {}).values()
                    for r in procedure['selection']['renderers']}
        allowed = max(r for r in self.meaning["audit_continuations"]["admitted_renderers"]
                      if r not in ex["refused"] and r not in selected)
        with mock.patch.object(api_runner, "_exclusive_run", side_effect=RuntimeError("past the refusal")), \
                self.assertRaisesRegex(RuntimeError, "past the refusal"):
            api_runner.execute(self._spec_at(allowed))

    def test_shared_request_builders_are_discovered_as_model_text(self):
        for module in ('shared_generation', 'typed_audit_runtime', 'typed_audit', 'audit_omissions', 'audit_batches'):
            relative = f'src/data_sheets_schema/{module}.py'
            with self.subTest(module=module):
                surface = _discovered()[0].files[relative]
                self.assertEqual(surface.roles['api'], 'model_facing')
                planted, _ = _plant(relative, "SCANNER_SENT_TEXT = 'Always describe the VOICE cohort.'", surface=surface)
                self.assertTrue(any(hit['violation'] and 'api' in hit['gates_in'] for hit in planted))

    def test_the_shape_follows_the_runner_phase_tables(self):
        from data_sheets_schema import api_runner
        model_phases = [p for p in api_runner.PHASES
                        if not (api_runner.CORE_DERIVED and p in api_runner.DERIVED_PHASES)]
        self.assertEqual(self.meaning["model_phases"], model_phases)
        self.assertGreater(len(model_phases), 1)
        for name, row in self.meaning["conditions"].items():
            with self.subTest(condition=name):
                self.assertEqual(row["shape"], "MULTI-PHASE")
                if row.get('selected_procedure'):
                    self.assertIsNone(row['model_calls_minimum'])
                    self.assertEqual(row['selected_procedure']['ordinary_model_phases'],
                                     [phase for phase in model_phases if phase != 'audit'])
                else:
                    self.assertEqual(row["model_calls_minimum"], len(model_phases))
        self.assertEqual(set(self.meaning["conditions"]), set(api_runner.CONDITION_PROMPTS))

    def test_the_follow_up_turns_follow_the_runner(self):
        """Re-addressing runs only under the receipt conditions, so `generic`
        (what the GitHub assistant runs) can never make it; build_readdress
        builds the full_readdress turn, not a second one (#4058)."""
        from data_sheets_schema import api_runner
        turns = self.meaning["followup_turns"]
        self.assertEqual(set(turns), {"full_readdress", "report_regate", "repair_{artifact}", "report_after_repair",
                                      "removal_repair_full", "full_receipt_completion",
                                      "typed_audit_worker", "typed_audit_omission", "typed_audit_integration"})
        self.assertEqual(turns["full_readdress"]["conditions"], sorted(api_runner.RECEIPT_CONDITIONS))
        for name in ("report_regate", "repair_{artifact}", "report_after_repair"):
            self.assertIsNone(turns[name]["conditions"])
        self.assertNotIn("full_readdress", self.meaning["conditions"]["generic"]["followup_turns"])
        self.assertIn("full_readdress", self.meaning["conditions"][self.cond["current"]]["followup_turns"])
        verdict = self.meaning["verdict"][0]
        self.assertIn("full_readdress runs only under", verdict)
        self.assertNotIn("readdress, ", verdict.replace("full_readdress", ""))

    def test_optional_repair_matches_real_spec_and_plan_without_changing_defaults(self):
        from data_sheets_schema import api_runner, removal_repair
        from dataclasses import replace
        turn = self.meaning["followup_turns"][removal_repair.PHASE]
        selection = turn["selection"]
        self.assertEqual(selection["field"], "removal_repair_version")
        self.assertEqual((selection["default"], selection["enabled_values"], selection["renderers"]), (0, [1], [8]))
        self.assertEqual(selection["runtime"], "api")
        self.assertTrue(turn["calls"][0].startswith("src/data_sheets_schema/removal_repair.py:"))
        self.assertTrue(turn["via"][0]["guards"])
        base = self._cli_spec()
        self.assertEqual(getattr(base, selection["field"]), selection["default"])
        self.assertFalse(any(s.startswith(removal_repair.PHASE + ":") for s in api_runner.plan(base)["conditional_calls"]))
        enabled = replace(base, removal_repair_version=1)
        self.assertTrue(any(s.startswith(removal_repair.PHASE + ":") for s in api_runner.plan(enabled)["conditional_calls"]))
        for changed in ({"removal_repair_version": True}, {"removal_repair_version": 2},
                        {"removal_repair_version": 1, "render_version": 7}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                replace(base, **changed)
        for row in self.meaning["conditions"].values():
            self.assertNotIn(removal_repair.PHASE, row["followup_turns"])
            if row.get('selected_procedure'):
                self.assertNotIn(removal_repair.PHASE, row['optional_followup_turns'])
            else:
                self.assertIn(removal_repair.PHASE, row["optional_followup_turns"])
        self.assertTrue(any("default 0 disables it" in text for text in self.meaning["verdict"]))

    def test_optional_receipt_completion_matches_real_spec_plan_and_registration(self):
        from data_sheets_schema import api_runner, chunking, receipt_completion, receipt_completion_policy
        from dataclasses import replace
        turn = self.meaning["followup_turns"][receipt_completion.PHASE]
        selection = turn["selection"]
        allowed = sorted(api_runner.RECEIPT_CONDITIONS)
        self.assertEqual(turn["conditions"], allowed)
        self.assertEqual(selection["conditions"], allowed)
        self.assertEqual(selection["field"], "receipt_completion_version")
        self.assertEqual((selection["default"], selection["enabled_values"], selection["renderers"]), (0, [1, 2, 3], [8, 25, 27]))
        legacy_allowed = {condition for case in selection['cases']
                          if case['values']['receipt_completion_version'] == 1 for condition in case['conditions']}
        self.assertEqual(selection["runtime"], "api")
        self.assertTrue(turn["calls"][0].startswith("src/data_sheets_schema/receipt_completion.py:"))
        self.assertTrue(turn["via"][0]["guards"])
        base = self._cli_spec()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        chunk_manifest = _write(Path(tmp.name) / "chunks.yaml",
                                chunking.dump_manifest(chunking.build_manifest(self.bundle)))
        self.assertFalse(any(s.startswith(receipt_completion.PHASE + ":") for s in api_runner.plan(base)["conditional_calls"]))
        for condition, row in self.meaning["conditions"].items():
            registration = {"format": receipt_completion_policy.FORMAT, "registration_id": "synthetic-scanner-only",
                            "condition": condition, "runtime_policy_sha256": receipt_completion.POLICY_SHA256,
                            "receipt_instrument_version": 4, "max_output_tokens": 1024, "max_request_bytes": 1000000,
                            "context_limit_tokens": 1000000, "context_limit_basis": "synthetic scanner test",
                            "coverage_floor": {"state": "pending", "mode": "diagnostic_pilot"}}
            encoded = json.dumps(registration)
            self.assertNotIn(receipt_completion.PHASE, row["followup_turns"])
            self.assertEqual(receipt_completion.PHASE in row["optional_followup_turns"], condition in allowed)
            if condition in legacy_allowed:
                receipt_completion_policy.parse_registration(encoded.encode())
                enabled = replace(base, condition=condition, chunk_manifest=chunk_manifest, receipt_completion_version=1,
                                  receipt_completion_registration=encoded)
                self.assertTrue(any(s.startswith(receipt_completion.PHASE + ":") for s in api_runner.plan(enabled)["conditional_calls"]))
            else:
                with self.subTest(condition=condition), self.assertRaisesRegex(ValueError, "receipt-producing condition"):
                    receipt_completion_policy.parse_registration(encoded.encode())
                with self.subTest(condition=condition), self.assertRaisesRegex(ValueError, "receipt-producing condition|requires shared generation"):
                    replace(base, condition=condition, receipt_completion_version=1,
                            receipt_completion_registration=encoded)

    def test_the_tuned_condition_inserts_its_component_and_never_its_prompt(self):
        """resolve_prompt inserts components/{PROJECT}.md into a tuned
        instruction and only names d4d_tuned_arm_prompt.md in a header line
        (#4058). Cross-checked on an offline rendering."""
        from data_sheets_schema import api_runner
        tuned = self.meaning["conditions"]["tuned"]
        self.assertEqual(tuned["appends"], ["src/download/prompts/components/{PROJECT}.md"])
        surface = _discovered()[0].files[self.cond["tuned_prompt"]]
        self.assertEqual(surface.roles["api"], "run_shaping")
        bundle = _write(Path(self.tmp.name) / "CHORUS_preprocessed.txt", "hello\n")
        from data_sheets_schema.cli import api as cli_api
        text = cli_api._spec("CHORUS", "baseline", "2026-09-30_probe", "tuned", bundle=str(bundle),
                             manifest=None).instruction
        component = (ROOT / api_runner.COMPONENTS / "CHORUS.md").read_text(encoding="utf-8").strip()
        self.assertIn(component[:80], text)
        prompt = (ROOT / api_runner.TUNED_PROMPT).read_text(encoding="utf-8")
        self.assertIn("## Substitution fields", prompt)
        self.assertNotIn("## Substitution fields", text)

    def test_shape_of_needs_one_call_no_turn_and_the_full_schema(self):
        self.assertEqual(scan.shape_of(["full"], [], True), "MONOLITHIC")
        self.assertNotEqual(scan.shape_of(["full"], [], False), "MONOLITHIC")
        self.assertEqual(scan.shape_of(["full"], ["repair"], True), "MULTI-PHASE")
        self.assertEqual(scan.shape_of(["full", "audit"], [], True), "MULTI-PHASE")

    def test_a_monolithic_runner_is_reported_monolithic(self):
        """One phase, no follow-up turn, the full schema: the conditions, the
        verdict and the arms all read MONOLITHIC; a schema digest makes the
        same single call not monolithic; a receipt-only turn makes only the
        receipt condition multi-phase (#4057, #4058)."""
        def meaning(**kw):
            with tempfile.TemporaryDirectory() as d:
                root = _synthetic_root(Path(d), **kw)
                facts = {"conditions": scan.condition_table(root), "controllers": {}, "legacy_scripts": []}
                return scan.api_meaning(root, facts)

        mono = meaning()
        self.assertEqual({c: v["shape"] for c, v in mono["conditions"].items()},
                         {"generic": "MONOLITHIC", "generic_v2": "MONOLITHIC"})
        self.assertEqual(mono["verdict"][0], "Live API conditions that are MONOLITHIC: generic, generic_v2.")
        self.assertTrue(all(v["shape"].startswith("MONOLITHIC ") for v in mono["arms"].values()))
        self.assertEqual(mono["native"]["shape"], "AGENTIC SINGLE-PHASE")
        self.assertIn("s_all.yaml", mono["native"]["schema_form"])

        digest = meaning(schema="digest_text('Dataset')")
        self.assertTrue(all(v["shape"].startswith("SINGLE-CALL") for v in digest["conditions"].values()))
        self.assertTrue(digest["verdict"][0].startswith("No live API condition"))
        self.assertIn("schema digest", digest["verdict"][0])

        receipt = meaning(planned='(["full_readdress: a re-address turn"] if spec.condition in RECEIPT_CONDITIONS '
                                  'else [])',
                          extra="\ndef _readdress(spec, client):\n    return _call(spec, 'full_readdress', client)\n")
        self.assertEqual({c: v["shape"] for c, v in receipt["conditions"].items()},
                         {"generic": "MONOLITHIC", "generic_v2": "MULTI-PHASE"})
        self.assertEqual(receipt["followup_turns"]["full_readdress"]["conditions"], ["generic_v2"])

        two = meaning(phases='("full", "audit")', heads=2)
        self.assertTrue(all(v["shape"].startswith("MULTI-PHASE") for v in two["arms"].values()))
        self.assertEqual(two["native"]["shape"], "AGENTIC MULTI-PHASE")

    def test_no_api_condition_is_a_runtime_hybrid(self):
        """Every native continuation of a parent run, at any renderer, sits in
        a package whose gate refuses a parent that is not agentic generic_v9
        at renderer 14. The registered API-only procedure can now select a
        renderer above that floor without admitting native work."""
        from data_sheets_schema import api_runner
        ac = self.meaning["audit_continuations"]
        self.assertFalse(ac["runtime_hybrid_possible"])
        self.assertEqual(ac["uncovered"], [])
        self.assertEqual(ac["ungated_continuations"], [])
        self.assertEqual({(g["path"], g["condition"], g["parent_renderer"]) for g in ac["gates"]},
                         {("notes/matched_cborg_2026-09-13/audit_controls/contract.py", "generic_v9", 14),
                          ("notes/matched_cborg_2026-09-13/finalization_controls/contract.py", "generic_v9", 14)})
        self.assertEqual({c["package"] for c in ac["continuations"]},
                         {"notes/matched_cborg_2026-09-13/audit_controls",
                          "notes/matched_cborg_2026-09-13/finalization_controls"})
        direct = [x for x in ac["setters"] if x["path"] == "notes/claudecode_direct/prepare_direct.py"]
        self.assertTrue(direct)
        for x in direct:
            self.assertIsNone(x["renderers"])               # a free --render-version option
            self.assertIn(x["runtime"], api_runner.AGENTIC_RUNTIMES)
        registered = [x for x in ac["setters"] if x["path"].endswith("prepare_registration.py")]
        self.assertTrue(registered and all(not x["reaches_floor"] for x in registered))
        self.assertTrue(ac["api_reaches_floor"])
        self.assertTrue(ac["api_cli_renderer_inputs"])
        self.assertEqual(ac["default_renderer"]["api"], self._cli_spec().render_version)
        self.assertLess(ac["default_renderer"]["api"], ac["floor"])
        selected = self.meaning['selected_procedures']['shared_generation_version']
        self.assertEqual(selected['selection']['renderers'], [25, 27])
        self.assertEqual(selected['selection']['conditions'], ['generic_v10',
            'generic_v10_source_heading_routing_v1', 'generic_v10_source_heading_span_v1'])
        self.assertEqual(set(selected['replaced_model_phases']['audit']),
                         {'typed_audit_worker', 'typed_audit_omission', 'typed_audit_integration'})
        self.assertEqual(selected['native_runtime'], 'not admitted by this API-only selector')
        self.assertIn('ordinary audit request', ac['api_path'])
        self.assertIn('source-derived selected audit replacement', ac['api_path'])
        self.assertNotIn('would stop at audit', ac['api_path'])
        for name, row in self.meaning["conditions"].items():
            with self.subTest(condition=name):
                self.assertFalse(row["runtime_hybrid"])
        line = next(v for v in self.meaning["verdict"] if v.startswith("No API condition is a runtime hybrid"))
        self.assertIn("prepare_direct.py", line)
        self.assertNotIn("set only by native audit continuations", line)
        for name, row in self.meaning['conditions'].items():
            if row.get('selected_procedure'):
                self.assertFalse(row['prompt_hybrid'])
                self.assertTrue(row['raw_prompt_body_references'])
                self.assertFalse(row['prompt_body_references'])
                self.assertIn('selected text', row['schema_form'])
                self.assertIn('schema_context', row['schema_form'])
                self.assertIn('before runtime substitutions', row['selected_template_adaptation']['basis'])
            else:
                self.assertEqual(row['prompt_hybrid'], bool(row['prompt_body_references']))

    def _continuations(self, files: dict[str, str]) -> dict:
        """audit_continuations over planted controller files, with the real
        runner and CLI."""
        runner = scan._tree(ROOT / scan.RUNNER)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(ROOT / "src/data_sheets_schema/cli", root / "src/data_sheets_schema/cli")
            for rel, text in files.items():
                _write(root / rel, text)
            return scan.audit_continuations(root, 20, sorted(r for r in files if r.endswith(".py")), runner,
                                            self.cond["agentic_runtimes"])

    def test_a_continuation_or_setter_that_could_continue_an_api_run_is_a_possible_hybrid(self):
        """Read in any spelling and at any renderer (#4055): a continuation
        with no agentic-parent gate, below the floor or inheriting its
        renderer, and a setter that can reach the floor by constant, by a
        free option or by arithmetic with neither a gate nor an agentic
        runtime, make a runtime hybrid possible; never a false "no"."""
        rebuild = "spec = RunSpec.from_render_spec(parent['render_spec'], project=parent['project'])\n"
        for why, files in (
                ("ungated continuation at 14", {"notes/c/prepare.py": rebuild + "m.update(render_version=14)\n"}),
                ("ungated continuation, inherited renderer",
                 {"notes/c/prepare.py": rebuild + "m.update(render_version=accepted['render_version'])\n"}),
                ("constant setter", {"notes/c/prepare.py": "RENDERER = 21\nm.update(protocol_version=7, "
                                                           "render_version=RENDERER)\n"}),
                ("free option", {"notes/c/prepare.py": "import argparse\np = argparse.ArgumentParser()\n"
                                                       "p.add_argument('--render-version', type=int, default=17)\n"
                                                       "def build(args):\n    return {'render_version': "
                                                       "args.render_version}\n"}),
                ("arithmetic", {"notes/c/prepare.py": "def build(parent):\n    return {'render_version': "
                                                      "parent['render_version'] + 6}\n"})):
            with self.subTest(why=why):
                self.assertTrue(self._continuations(files)["runtime_hybrid_possible"])

    def test_a_gated_continuation_or_an_agentic_generation_is_not_a_hybrid(self):
        gate = ("def check(spec):\n    if spec.condition != 'generic_v9' or spec.render_version != 14 "
                "or not spec.is_agentic:\n        raise ValueError('parent')\n")
        rebuild = "spec = RunSpec.from_render_spec(parent['render_spec'], project=parent['project'])\n"
        for why, files in (
                ("gated continuation", {"notes/c/prepare.py": rebuild + "m.update(render_version=21)\n",
                                        "notes/c/contract.py": gate}),
                ("free option, agentic runtime",
                 {"notes/c/prepare.py": "import argparse\nRUNTIME = 'Claude Code'\np = argparse.ArgumentParser()\n"
                                        "p.add_argument('--render-version', type=int, default=17)\n"
                                        "def build(args):\n    return RunSpec(runtime=RUNTIME, "
                                        "render_version=args.render_version)\n"}),
                ("options below the floor",
                 {"notes/c/prepare.py": "import argparse\np = argparse.ArgumentParser()\n"
                                        "p.add_argument('--render-version', type=int, choices=(9, 10), default=9)\n"
                                        "def build(args):\n    return {'render_version': args.render_version}\n"})):
            with self.subTest(why=why):
                self.assertFalse(self._continuations(files)["runtime_hybrid_possible"])

    def test_only_a_gate_that_refuses_every_non_agentic_parent_counts(self):
        """A guard on the condition alone, one that refuses agentic parents,
        an unrelated raise, and one that refuses a non-agentic parent only
        under another condition, each leave an API parent admitted (#4057)."""
        prepare = ("spec = RunSpec.from_render_spec(parent['render_spec'], project=parent['project'])\n"
                   "m.update(render_version=21)\n")
        for why, contract in (
                ("condition only", "def check(spec):\n    if spec.condition != 'generic_v9':\n        raise "
                                   "ValueError('parent')\n\ndef note(spec):\n    return spec.is_agentic\n"),
                ("refuses agentic parents", "def check(spec):\n    if spec.is_agentic:\n        raise ValueError('x')\n"),
                ("unrelated raise", "def check(spec):\n    # is_agentic is checked elsewhere\n    if spec.bundle is "
                                    "None:\n        raise ValueError('x')\n"),
                ("partial", "def check(spec, strict):\n    if strict and not spec.is_agentic:\n        raise "
                            "ValueError('x')\n")):
            with self.subTest(why=why):
                got = self._continuations({"notes/c/prepare.py": prepare, "notes/c/contract.py": contract})
                self.assertTrue(got["runtime_hybrid_possible"])
                self.assertEqual(got["gates"], [])

    def test_an_api_path_that_selects_the_floor_is_reported_not_a_hybrid(self):
        runner = scan._tree(ROOT / scan.RUNNER)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / scan.CLI_API, (ROOT / scan.CLI_API).read_text(encoding="utf-8")
                   + '\n@click.option("--render-version", type=int)\ndef _x(): pass\n')
            got = scan.audit_continuations(root, 20, [], runner, self.cond["agentic_runtimes"])
        self.assertTrue(got["api_reaches_floor"])
        self.assertFalse(got["runtime_hybrid_possible"])

    def test_legacy_cli_without_renderer_selection_remains_below_the_floor(self):
        runner = scan._tree(ROOT / scan.RUNNER)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / scan.CLI_API, 'def legacy():\n    return RunSpec()\n')
            got = scan.audit_continuations(root, 20, [], runner, self.cond['agentic_runtimes'])
        self.assertFalse(got['api_reaches_floor'])
        self.assertFalse(got['runtime_hybrid_possible'])
        self.assertEqual(got['api_cli_renderer_inputs'], [])
        self.assertNotIn('selected audit replacement', got['api_path'])

    def test_renderer_values_are_read_in_any_spelling(self):
        """Literal, conditional, local, constant, option with or without
        choices, inherited (with its default), and arithmetic (#4055)."""
        tree = ast.parse("import argparse\nR = 21\np = argparse.ArgumentParser()\n"
                         "p.add_argument('--render-version', type=int, choices=range(9, 12), default=9)\n"
                         "p.add_argument('--other-render', dest='free_render', type=int, default=17)\n"
                         "def f(args, job, spec):\n    local = 22\n    return [21 if args else 20, local, R, "
                         "args.render_version, args.free_render, job['render_version'], "
                         "job.get('render_version', 9), spec.render_version, job['render_version'] + 1]\n")
        fn = scan._function(tree, "f")
        options = scan._renderer_options(tree)
        consts = {"R": 21}
        exprs = fn.body[-1].value.elts
        got = [scan._renderer_value(e, fn, consts, options)[0] for e in exprs]
        self.assertEqual(got, [[20, 21], [22], [21], [9, 10, 11], None, [], [9], [], None])


class TestDerivationsFailLoudly(unittest.TestCase):
    """Each derivation reads the code that decides it in any spelling, and
    finds-nothing is "not derived" (exit 2), never a fallback (#4025)."""

    @classmethod
    def setUpClass(cls):
        cls.runner_text = (ROOT / scan.RUNNER).read_text(encoding="utf-8")
        cls.cli_text = (ROOT / scan.CLI_API).read_text(encoding="utf-8")

    def _build(self, text):
        return scan._function(ast.parse(text), "build_phase")

    def test_the_audit_floor_survives_a_reordered_guard_and_fails_without_one(self):
        guard = 'if spec.render_version >= 20 and phase == "audit":'
        self.assertIn(guard, self.runner_text)
        live = scan.derive_agentic_audit_from(self._build(self.runner_text))
        reordered = self.runner_text.replace(guard, 'if phase == "audit" and spec.render_version >= 20:')
        self.assertEqual(scan.derive_agentic_audit_from(self._build(reordered)), live)
        flipped = self.runner_text.replace(guard, 'if "audit" == phase and 20 <= spec.render_version:')
        self.assertEqual(scan.derive_agentic_audit_from(self._build(flipped)), live)
        gone = self.runner_text.replace(guard, "if False:")
        with self.assertRaisesRegex(scan.ConfigError, "not derived"):
            scan.derive_agentic_audit_from(self._build(gone))

    def test_the_default_renderer_is_read_in_either_form_or_not_at_all(self):
        line = "self.render_version = 7 if self.is_agentic else 8"
        self.assertIn(line, self.runner_text)
        self.assertEqual(scan.derive_default_renderer(ast.parse(self.runner_text)), {"agentic": 7, "api": 8})
        negated = self.runner_text.replace(line, "self.render_version = 8 if not self.is_agentic else 7")
        self.assertEqual(scan.derive_default_renderer(ast.parse(negated)), {"agentic": 7, "api": 8})
        with self.assertRaisesRegex(scan.ConfigError, "not derived"):
            scan.derive_default_renderer(ast.parse(self.runner_text.replace(line, "self.render_version = 8")))

    def test_the_cli_default_is_read_in_either_form_or_not_at_all(self):
        prompts = _discovered()[1]["conditions"]["prompts"]
        line = 'condition, kw["condition_stated"] = "generic", False'
        self.assertIn(line, self.cli_text)
        self.assertEqual(scan.derive_cli_default(ast.parse(self.cli_text), prompts), "generic")
        v2 = self.cli_text.replace(line, 'condition = "generic_v2"; kw["condition_stated"] = False')
        self.assertEqual(scan.derive_cli_default(ast.parse(v2), prompts), "generic_v2")
        for broken, why in ((self.cli_text.replace(line, "pass"), "assigns nothing"),
                            (self.cli_text.replace(line, 'condition = "generic_v99"'), "not in")):
            with self.subTest(why=why), self.assertRaisesRegex(scan.ConfigError, why):
                scan.derive_cli_default(ast.parse(broken), prompts)

    def test_a_runner_table_that_cannot_be_read_is_not_derived(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / scan.CLI_API, self.cli_text)
            for name in ("PHASES", "CORE_DERIVED", "RECEIPT_CONDITIONS"):
                broken = re.sub(rf"(?m)^{name} = ", f"{name}_GONE = ", self.runner_text)
                _write(root / scan.RUNNER, broken)
                with self.subTest(name=name), \
                        self.assertRaisesRegex(scan.ConfigError, f"not derived: api_runner.{name}"):
                    scan.condition_table(root)

    def test_follow_up_turns_that_cannot_be_read_are_not_derived(self):
        """A model call whose phase cannot be read, and a plan() with no
        conditional_calls, stop the scan rather than drop a turn (#4058)."""
        tree = ast.parse(self.runner_text)
        consts = scan._module_constants(ROOT / scan.RUNNER)
        phases = list(consts["PHASES"])
        scan.derive_followups(tree, phases, consts, root=ROOT)
        call = '_call_with_usage(spec, "full_readdress", 1, started,'
        self.assertIn(call, self.runner_text)
        unread = ast.parse(self.runner_text.replace(call, "_call_with_usage(spec, pick_phase(), 1, started,"))
        with self.assertRaisesRegex(scan.ConfigError, "not derived: the follow-up turns"):
            scan.derive_followups(unread, phases, consts, root=ROOT)
        no_plan = ast.parse(self.runner_text.replace('"conditional_calls":', '"other_calls":'))
        with self.assertRaisesRegex(scan.ConfigError, "conditional_calls"):
            scan.derive_followups(no_plan, phases, consts, root=ROOT)

    def test_the_tuned_text_the_toolchain_and_the_arms_are_not_derived_when_gone(self):
        env = scan._module_constants(ROOT / scan.RUNNER)
        block = 'if spec.condition == "tuned":'
        self.assertIn(block, self.runner_text)
        with self.assertRaisesRegex(scan.ConfigError, "tuned"):
            scan.derive_tuned_reads(ast.parse(self.runner_text.replace(block, 'if spec.condition == "x":')), env)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            text = (ROOT / scan.AGENTIC_RUNTIME).read_text(encoding="utf-8")
            _write(root / scan.AGENTIC_RUNTIME, re.sub(r"(?m)^SCHEMAS = ", "SCHEMAS_GONE = ", text))
            with self.assertRaisesRegex(scan.ConfigError, "native toolchain"):
                scan.derive_toolchain(root)
            _write(root / scan.CLI_API, self.cli_text.replace("_healthsheet_only.txt", "_hs.txt"))
            with self.assertRaisesRegex(scan.ConfigError, "deterministic arm commands"):
                scan.deterministic_arm_commands(root)

    def test_the_request_and_the_model_inputs_are_read_in_either_form_or_not_at_all(self):
        """The request type is what `build_phase` returns, directly or
        through a local; a `build_phase` that returns no construction of a
        runner class, a request type without a text field, and an arm with
        no bundle pattern are not derived (#4085)."""
        ret = "    return PhaseRequest(\n        phase=phase,"
        self.assertEqual(self.runner_text.count(ret), 1)
        cases = {"through a local": self.runner_text.replace(ret, "    req = PhaseRequest(\n        phase=phase,"
                                                              ).replace("        messages=[{\"role\": \"user\", "
                                                                        "\"content\": parts}],\n    )\n",
                                                                        "        messages=[{\"role\": \"user\", "
                                                                        "\"content\": parts}],\n    )\n"
                                                                        "    return req\n", 1)}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write(root / scan.RUNNER, self.runner_text)
            live = scan.derive_request_type(root)
            self.assertEqual(live["class"], "PhaseRequest")
            for why, text in cases.items():
                self.assertIn("    return req\n", text)
                _write(root / scan.RUNNER, text)
                with self.subTest(why=why):
                    self.assertEqual(scan.derive_request_type(root), live)
            for broken, why in ((self.runner_text.replace(ret, "    return dict(\n        phase=phase,"),
                                 "returns a construction of"),
                                (self.runner_text.replace("    messages: list[dict[str, Any]] = field(",
                                                          "    turns: list[dict[str, Any]] = field("),
                                 "has no field messages")):
                _write(root / scan.RUNNER, broken)
                with self.subTest(why=why), self.assertRaisesRegex(scan.ConfigError, why):
                    scan.derive_request_type(root)
            _write(root / scan.CLI_API, self.cli_text.replace('"{p}_healthsheet_only.txt"', '"healthsheet.txt"'))
            with self.assertRaisesRegex(scan.ConfigError, "not derived: the model input files"):
                scan.model_input_files(root, [])

    def test_a_runner_that_branches_on_the_arm_is_not_derived(self):
        with tempfile.TemporaryDirectory() as d:
            root = _synthetic_root(Path(d), extra="\ndef _x(spec):\n    if spec.arm == 'other':\n        pass\n")
            facts = {"conditions": scan.condition_table(root), "controllers": {}, "legacy_scripts": []}
            with self.assertRaisesRegex(scan.ConfigError, "arms' shape"):
                scan.api_meaning(root, facts)


class TestWhatTextsRun(unittest.TestCase):
    """The imports of every script a playbook, agent or instruction runs, and
    every CLI group they run, are followed (#4091)."""

    @classmethod
    def setUpClass(cls):
        cls.surfaces, cls.facts = _discovered()

    def test_the_renderer_behind_the_shim_the_instructions_run_is_a_surface(self):
        """d4d_assistant_create.md runs `src/html/human_readable_renderer.py`,
        a shim whose code is in the rendering module it imports. The closure
        stops at the CLI package, whose groups are followed where run."""
        shim, impl = "src/html/human_readable_renderer.py", "src/data_sheets_schema/rendering/human_readable_renderer.py"
        self.assertIn(impl, self.facts["run_script_imports"][shim])
        self.assertIn("src/data_sheets_schema/cli/__init__.py", self.facts["run_script_imports"][shim])
        self.assertEqual(self.surfaces.files[impl].roles, {"native_agentic": "run_shaping"})
        self.assertEqual(self.surfaces.files[impl].runs, set())
        self.assertNotIn("src/data_sheets_schema/cli/evaluate.py", self.surfaces.files)

    def test_a_code_table_in_what_a_run_script_imports_is_a_violation(self):
        """The 'Diabetes Status' table of AI-READI's study groups gates, and a
        project list planted in the module does too."""
        rel = "src/data_sheets_schema/rendering/human_readable_renderer.py"
        lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        at = next(i for i, x in enumerate(lines, 1) if "'diabetes', 'dm'" in x)
        hits = [h for h in _scan_text(rel, "\n".join(lines) + "\n", self.surfaces.files[rel]) if h["line"] == at]
        self.assertEqual({(h["match"].lower(), h["context"]) for h in hits}, {("diabet", "code_table")})
        self.assertTrue(all(h["violation"] and h["gates_in"] == ["native_agentic"] for h in hits))
        planted, _ = _plant(rel, 'RENDER_PROJECTS_4091 = ["CHORUS"]')
        self.assertTrue(planted and all(h["violation"] for h in planted))

    def test_a_run_script_imports_from_its_directory_and_stops_at_the_cli(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            _write(root / "src/html/run_4091.py", "import sibling_4091\n"
                                                  "from data_sheets_schema.rendering.impl_4091 import x\n")
            _write(root / "src/html/sibling_4091.py", "Y = 1\n")
            _write(root / "src/data_sheets_schema/rendering/impl_4091.py",
                   "x = ['diabetes']\ndef main():\n    from data_sheets_schema.cli import cli\n")
            _write(root / "src/data_sheets_schema/cli/__init__.py", "from . import evaluate\n")
            _write(root / "src/data_sheets_schema/cli/evaluate.py", "PROJECTS = ['CHORUS']\n")
            cli = frozenset({(root / scan.CLI_PACKAGE[0]).resolve()})
            members, _ = scan._code_closure(root, [root / "src/html/run_4091.py"], set(), dirs=["src/html"],
                                            opaque=cli)
            names = {p.relative_to(root).as_posix() for p in members}
        self.assertEqual(names, {"src/html/run_4091.py", "src/html/sibling_4091.py",
                                 "src/data_sheets_schema/rendering/impl_4091.py",
                                 "src/data_sheets_schema/cli/__init__.py"})

    def test_every_cli_group_a_playbook_or_agent_runs_is_followed(self):
        """/d4d-agent and /d4d-assistant run `d4d utils status`; the exposed
        d4d-review-record agent runs `d4d review`, which is exposed."""
        groups = self.facts["cli_groups"]["native_agentic"]
        self.assertIn(".claude/commands/d4d-agent.md", groups["utils"]["by"])
        self.assertEqual(groups["utils"]["role"], "run_shaping")
        self.assertIn("utils", self.facts["native_cli_groups"])
        self.assertEqual(self.surfaces.files["src/data_sheets_schema/cli/utils.py"].roles,
                         {"native_agentic": "run_shaping"})
        self.assertEqual(groups["review"]["role"], "exposed")
        self.assertEqual(self.surfaces.files["src/data_sheets_schema/cli/review.py"].roles,
                         {"native_agentic": "exposed"})
        self.assertEqual(scan._cli_groups(ROOT, "run `d4d utils status --quick`, then `python -m "
                                                "data_sheets_schema.cli provenance record x`; /d4d-full-core "
                                                "and d4d nosuch run are not groups"), ["provenance", "utils"])


class TestSessionDescriptions(unittest.TestCase):
    """Claude Code lists the name and description of every command, agent
    and skill in every interactive session; a body loads only when it is
    invoked (#4091)."""

    def test_the_lines_a_session_lists(self):
        agent = ("---\nname: a-4091\ndescription: |\n  When to use: x.\n  Examples:\n"
                 "    - \"Review the CHORUS record\"\nmodel: inherit\n---\n\nBody naming VOICE.\n")
        self.assertEqual(scan.session_description_lines(agent),
                         [(2, 2, "frontmatter name"), (3, 6, "frontmatter description")])
        self.assertEqual(scan.session_description_lines("# Generate a CM4AI datasheet\n\nBody.\n"),
                         [(1, 1, "description (the first line)")])
        self.assertEqual(scan.session_description_lines("---\nname: c\n---\n\nFirst line of the body.\n"),
                         [(2, 2, "frontmatter name"), (5, 5, "description (the first line)")])

    def test_every_command_agent_and_skill_lists_its_description_in_a_session(self):
        surfaces, facts = _discovered()
        for rel in (".claude/agents/d4d-review-record.md", ".claude/commands/README.md",
                    ".claude/commands/d4d-full-core.md", ".claude/skills/review-open-issues/SKILL.md"):
            with self.subTest(rel=rel):
                self.assertEqual(surfaces.files[rel].roles["interactive_session"], "exposed")
                self.assertTrue(surfaces.files[rel].loaded["interactive_session"])
                self.assertIn(rel, facts["interactive"]["described"])

    def test_a_token_in_a_description_is_an_interactive_session_violation(self):
        """In an agent's description, in a command's first line; the same
        token in the body is exposed and never gates."""
        rel = ".claude/agents/d4d-schema-expert.md"
        planted, _ = _plant(rel, '    - "Describe the CM4AI release"', after="Examples:")
        self.assertTrue(planted)
        self.assertTrue(all(h["violation"] and h["gates_in"] == SESSION_GATES for h in planted), planted)
        body, _ = _plant(rel, "Prefer the CM4AI release notes.")
        self.assertTrue(body and not any(h["violation"] for h in body))
        readme = ".claude/commands/README.md"
        text = (ROOT / readme).read_text(encoding="utf-8").splitlines()
        first = next(i for i, x in enumerate(text) if x.strip())
        text[first] += " for CM4AI"
        hits = [h for h in _scan_text(readme, "\n".join(text) + "\n", _discovered()[0].files[readme])
                if h["line"] == first + 1]
        self.assertTrue(hits and all(h["violation"] and h["gates_in"] == SESSION_GATES for h in hits))


class TestRawYamlComments(unittest.TestCase):
    """A comment in a YAML file counts where a text names the file for the
    model to Read: the Read tool returns it raw (#4091). The digest drops it,
    so a comment in a schema module only the digest renders never gates."""

    def test_a_yaml_comment_counts_where_a_text_names_the_file_for_reading(self):
        surfaces, _ = _discovered()
        core = "src/data_sheets_schema/schema/D4D_Core.yaml"
        self.assertIn("native_agentic", surfaces.files[core].raw)
        self.assertNotIn("shared_schema", surfaces.files[core].raw)
        planted, _ = _plant(core, "# Record the CHORUS release identifiers here.")
        self.assertTrue(planted)
        self.assertTrue(all(h["violation"] and h["gates_in"] == ["native_agentic"] and h["context"] == "comment"
                            and h["read_raw"] for h in planted), planted)
        human = "src/data_sheets_schema/schema/D4D_Human.yaml"
        self.assertEqual(surfaces.files[human].roles, {"shared_schema": "model_facing"})
        digest_only, _ = _plant(human, "# Record the CHORUS release identifiers here.")
        self.assertTrue(digest_only and not any(h["violation"] for h in digest_only))


class TestRunShapingYamlAndShell(unittest.TestCase):
    """A workflow, a config and a shell script decide what runs: a branch on
    a project, a project default and a per-project key there gate (#4091)."""

    def _units(self, text: str, code: bool = True) -> dict:
        """token -> contexts of the units holding it, per line."""
        out: dict = {}
        for line, ctx, unit, _ in scan.units_for(Path("x.yml"), "x.yml", text, code=code):
            for _, _, tok, matched in scan.match_text(unit, list(_tokens())):
                out.setdefault((line, matched), set()).add(ctx)
        return out

    def test_shell_branches_defaults_and_tables(self):
        cases = (('if [ "$P" = "CHORUS" ]; then', "CHORUS", {"code_branch"}),
                 ("[[ $P == VOICE* ]] && echo y", "VOICE", {"code_branch"}),
                 ("if grep -q CM4AI notes.txt; then", "CM4AI", {"code_branch"}),
                 ('P="${P:-CM4AI}"', "CM4AI", {"code_table"}),
                 ("d4d api run --project AI_READI --yes", "AI_READI", {"code_table"}),
                 ("d4d api run --project=AI_READI", "AI_READI", {"code_table"}),
                 ("for p in CHORUS VOICE; do", "CHORUS", {"code_table"}),
                 ("PROJECTS=(CHORUS VOICE)", "VOICE", {"code_table"}),
                 ("DATASET=CHORUS", "CHORUS", {"code_table"}),
                 ('echo "Processing CHORUS now"', "CHORUS", {"value"}),
                 ('MSG="see the CHORUS docs"', "CHORUS", {"value"}),
                 ("# a CHORUS comment", "CHORUS", {"comment"}))
        for line, token, want in cases:
            with self.subTest(line=line):
                got = {c for _, c, unit, _ in scan._shell_units(line) if token in unit}
                self.assertEqual(got, want)
        case = 'case "$P" in\n  CHORUS|VOICE) X=1 ;;\n  *) X=2 ;;\nesac\n'
        got = {(n, unit.strip(), c) for n, c, unit, _ in scan._shell_units(case) if c != "value"}
        self.assertTrue({(2, "CHORUS", "code_branch"), (2, "VOICE", "code_branch"), (2, "1", "code_table"),
                         (3, "*", "code_branch")} <= got, got)

    def test_workflow_expressions_scripts_and_config_tables(self):
        text = ("jobs:\n"                                                           # 1
                "  go:\n"                                                           # 2
                "    if: github.event.inputs.dataset == 'CHORUS'\n"                 # 3
                "    steps:\n"                                                      # 4
                "      - name: Run for the VOICE study\n"                           # 5
                "        run: |\n"                                                  # 6
                '          if [ "$D" = "CM4AI" ]; then echo y; fi\n'                # 7
                '          echo "the AI_READI notes"\n'                             # 8
                "        env:\n"                                                    # 9
                "          P: ${{ inputs.project || 'VOICE_PEDIATRIC' }}\n"         # 10
                "      - uses: actions/github-script@v7\n"                          # 11
                "        with:\n"                                                   # 12
                "          script: |\n"                                             # 13
                "            if (p === 'aireadi') { x = 1; }\n"                     # 14
                "            const d = 'cm4ai';\n"                                  # 15
                "            console.log('see the CHORUS page');\n"                 # 16
                "CM4AI:\n"                                                          # 17
                "  temperature: 0\n"                                                # 18
                "description: CHORUS\n"                                             # 19
                "src/download/prompts/components/CHORUS.md:\n"                      # 20
                "  sha256: abc\n")                                                  # 21
        got = self._units(text)
        self.assertEqual(got, {(3, "CHORUS"): {"code_branch"}, (5, "VOICE"): {"value"},
                               (7, "CM4AI"): {"code_branch"}, (8, "AI_READI"): {"value"},
                               (10, "VOICE_PEDIATRIC"): {"code_table"}, (14, "aireadi"): {"code_branch"},
                               (15, "cm4ai"): {"code_table"}, (16, "CHORUS"): {"value"},
                               (17, "CM4AI"): {"code_table"}, (19, "CHORUS"): {"prose"},
                               (20, "CHORUS"): {"value"}})
        # a file some approach hands to a model keeps the YAML contexts
        self.assertFalse({c for v in self._units(text, code=False).values() for c in v} & scan.CODE_CONTEXTS)

    def test_project_branches_planted_in_the_workflow_config_and_shell_gate(self):
        """The reviewer's plants (#4091): a shell branch, a default in an
        expression, a github-script branch and a step `if:` in the workflow,
        a per-project key in the config, a branch in the prerequisite
        script. Text in the same files stays run-shaping text."""
        wf, config = ".github/workflows/d4d-agent.yml", ".github/workflows/d4d_assistant_deterministic.config"
        shell = "src/github/validate_prerequisites.sh"
        for rel, line, after, token, ctx in (
                (wf, '          if [ "$DATASET" = "CHORUS" ]; then echo special; fi', "set -euo pipefail",
                 "CHORUS", "code_branch"),
                (wf, "          D=${{ steps.resolve.outputs.dataset || 'VOICE' }}", "set -euo pipefail",
                 "VOICE", "code_table"),
                (wf, "            if (itemType === 'AI_READI') { core.setOutput('x', 'y'); }",
                 "const isAllowed = allowedUsers.includes(userLogin);", "AI_READI", "code_branch"),
                (wf, "        if: steps.resolve.outputs.dataset != 'CM4AI'", "- name: Validate against the schema",
                 "CM4AI", "code_branch"),
                (config, "CM4AI:\n  temperature: 0.0", None, "CM4AI", "code_table"),
                (shell, 'if [ "$DATASET" = "VOICE" ]; then echo x; fi', None, "VOICE", "code_branch")):
            with self.subTest(rel=rel, token=token):
                planted, _ = _plant(rel, line, after)
                hits = [h for h in planted if h["match"] == token]
                self.assertTrue(hits)
                self.assertTrue(all(h["context"] == ctx and h["violation"] for h in hits), hits)
        quiet, _ = _plant(wf, '          echo "Generating the CHORUS datasheet"', "set -euo pipefail")
        self.assertTrue(quiet and not any(h["violation"] for h in quiet))

    def test_a_membership_test_on_a_fromjson_list_is_a_branch(self):
        """`contains(fromJSON('[...]'), x)` is GitHub's membership test on a
        literal list: a branch, like `x == 'A'`; any other fromJSON literal
        is data the expression reads, a table (#4130)."""
        test = "contains(fromJSON('[\"CHORUS\", \"VOICE\"]'), steps.resolve.outputs.dataset)"
        self.assertEqual([c for *_, c in scan._expr_spans(test)], ["code_branch"])
        self.assertEqual([c for *_, c in scan._expr_spans("fromJSON('{\"CHORUS\": \"a\"}')[inputs.p]")], ["code_table"])
        wf = ".github/workflows/d4d-agent.yml"
        planted, _ = _plant(wf, "        if: contains(fromJSON('[\"CHORUS\", \"VOICE\"]'), steps.resolve.outputs.dataset)",
                            "- name: Validate against the schema")
        self.assertEqual({h["match"] for h in planted}, {"CHORUS", "VOICE"})
        self.assertTrue(all(h["context"] == "code_branch" and h["violation"] for h in planted), planted)

    def test_run_shaping_json_is_read_as_code(self):
        """A JSON file no approach hands to a model (the project settings, the
        assistant's allow-list) is data that shapes a run: a key and a string
        value without whitespace are table entries, a hook command is shell
        (with JSON escapes too: the next test), a sentence stays text
        (#4130)."""
        text = ('{\n'                                                                                       # 1
                '  "env": {"D4D_MANIFEST": "data/preprocessed/CHORUS_manifest.yaml", "NOTE": "see the VOICE notes"},\n'
                '  "CM4AI": ["a", "AI_READI"],\n'                                                            # 3
                '  "hooks": {"PreToolUse": [{"type": "command", "command": "python3 x.py --project VOICE"}]}\n'  # 4
                '}\n')
        got: dict = {}
        for line, ctx, unit, _ in scan.units_for(Path("s.json"), "s.json", text, code=True):
            for _, _, _, matched in scan.match_text(unit, list(_tokens())):
                got.setdefault((line, matched), set()).add(ctx)
        self.assertEqual(got, {(2, "CHORUS"): {"code_table"}, (2, "VOICE"): {"value"}, (3, "CM4AI"): {"code_table"},
                               (3, "AI_READI"): {"code_table"}, (4, "VOICE"): {"code_table"}})
        handed = {c for _, c, _, _ in scan.units_for(Path("s.json"), "s.json", text, code=False)}
        self.assertEqual(handed, {"value"})
        surfaces = _discovered()[0]
        for rel, approaches in ((".claude/settings.json", SESSION_GATES),
                                (".github/ai-controllers.json", ["github_assistant"])):
            with self.subTest(rel=rel):
                self.assertEqual(surfaces.files[rel].roles, dict.fromkeys(approaches, "run_shaping"))

    def test_a_json_hook_command_with_escapes_is_read_as_shell(self):
        """A hook `command` is read as the shell gets it: its JSON escapes
        decoded (`\\"`, `\\\\`, `\\n`), and each span mapped back to the line as
        written, so a unit is the text there (#4142). Any backslash used to
        turn the shell reading off. A quoted value with whitespace stays text,
        as it does unescaped."""
        cases = (('\\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/x.py --project CHORUS', {("code_table", "CHORUS")}),
                 ('python3 x.py --note \\"a b\\" --project CHORUS', {("code_table", "CHORUS")}),
                 ('P=${P:-CHORUS} python3 \\"x.py\\"', {("code_table", "CHORUS")}),
                 ('python3 \\\\srv\\\\x.py --project \\"CHORUS\\"', {("code_table", '\\"CHORUS\\"')}),
                 ('cd x\\nif [ \\"$P\\" = \\"CHORUS\\" ]; then y; fi', {("code_branch", '\\"CHORUS\\"')}),
                 ('\\tpython3 x.py --project=CHORUS', {("code_table", "CHORUS")}))
        for command, want in cases:
            line = '{"hooks": {"PreToolUse": [{"type": "command", "command": "' + command + '"}]}}'
            json.loads(line)
            got = {(ctx, unit) for _, ctx, unit, _ in scan._json_code_units(line)
                   for *_, matched in scan.match_text(unit, list(_tokens())) if matched == "CHORUS"}
            with self.subTest(command=command):
                self.assertEqual(got, want)
        line = '{"command": "python3 x.py --project \\"CHORUS data\\""}'
        self.assertEqual({ctx for _, ctx, unit, _ in scan._json_code_units(line) if "CHORUS" in unit}, {"value"})
        # the decoding and its map back to the text as written
        for body in ('a\\"b\\\\c\\/d\\b\\f\\n\\r\\t', '\\u0041\\u00e9x', '\\ud83d\\ude00y', '\\ud83dz', 'plain'):
            decoded, at = scan._json_decoded(body)
            with self.subTest(body=body):
                self.assertEqual(decoded, json.loads(f'"{body}"'))
                self.assertEqual(len(at), len(decoded) + 1)
                self.assertEqual([json.loads('"' + body[at[k]:at[k + 1]] + '"') for k in range(len(decoded))],
                                 list(decoded))
        # end to end, the reviewer's three forms under the role discovery
        # gives the project settings
        for command, _want in cases[:3]:
            with self.subTest(planted=command):
                planted, _ = _plant(".claude/settings.json", f'            "command": "{command}"',
                                    '"command": "$CLAUDE_PROJECT_DIR/.claude/hooks/protect_schema_hook.py"')
                hits = [h for h in planted if h["match"] == "CHORUS"]
                self.assertEqual([(h["context"], h["violation"], h["gates_in"]) for h in hits],
                                 [("code_table", True, SESSION_GATES)])


class TestParseFailures(unittest.TestCase):
    """A Python file the scan cannot parse stops it with exit 2 and is
    named, as an unreadable surface is; it is never classed as having
    nothing that gates (#4092)."""

    BROKEN = "def broken(:\n    PROJECTS = ['CHORUS']\n"

    def test_a_python_surface_that_does_not_parse_raises(self):
        with tempfile.TemporaryDirectory() as d:
            _write(Path(d) / "bad_4092.py", self.BROKEN)
            surface = scan.Surface("bad_4092.py", ["run_controllers"], "run_shaping", "live", "t")
            with self.assertRaisesRegex(scan.UnparsedSurface, "bad_4092.py"):
                scan.scan_file(Path(d), surface, list(_tokens()))
        with self.assertRaises(SyntaxError):
            list(scan._python_units(self.BROKEN))

    def test_an_unparsed_surface_is_exit_2_and_named(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copy(ROOT / scan.NEUTRALITY_TEST, _write(root / scan.NEUTRALITY_TEST, ""))
            _write(root / "notes/bad_4092.py", self.BROKEN)
            surfaces = scan.Surfaces()
            surfaces.add("notes/bad_4092.py", "run_controllers", "run_shaping", "live", "test")
            with mock.patch.object(scan, "discover", return_value=(surfaces, {})), mock.patch("sys.stderr", err), \
                    mock.patch("sys.stdout"):
                code = scan.main(["--root", str(root), "--report", str(root / "r.md")])
            self.assertFalse((root / "r.md").exists())
            self.assertFalse((root / "r.json").exists())
        self.assertEqual(code, 2)
        self.assertIn("notes/bad_4092.py", err.getvalue())
        self.assertIn("cannot be parsed", err.getvalue())
        self.assertIn(sys.executable, err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_discovery_refuses_a_module_it_cannot_parse(self):
        """A controller or model client that does not parse could not be
        discovered: discovery stops and names it with the interpreter."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            _write(root / "notes/exp_4092/launch.py", "from data_sheets_schema.api_runner import RunSpec\n"
                   + self.BROKEN)
            with self.assertRaisesRegex(scan.ConfigError, r"cannot be parsed by .*notes/exp_4092/launch\.py"):
                scan.discover(root)

    def test_a_closure_or_a_test_listing_that_reaches_an_unparsable_file_stops(self):
        """An import closure does not drop a module it cannot parse, and the
        test listing does not skip a test of generation it cannot parse."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            _write(root / "src/data_sheets_schema/cli/arm_4092.py", "from data_sheets_schema.helper_4092 import x\n")
            _write(root / "src/data_sheets_schema/helper_4092.py", self.BROKEN)
            _write(root / "tests/test_x_4092.py", "from data_sheets_schema.api_runner import build_phase\n"
                   + self.BROKEN)
            with self.assertRaisesRegex(scan.ConfigError, "helper_4092.py"):
                scan._code_closure(root, [root / "src/data_sheets_schema/cli/arm_4092.py"], set())
            with self.assertRaisesRegex(scan.ConfigError, "helper_4092.py"):
                scan._package_closure(root, ["data_sheets_schema.cli.arm_4092"])
            with self.assertRaisesRegex(scan.ConfigError, "tests/test_x_4092.py"):
                scan.scan_tests(root, list(_tokens()))


class TestLaunchFlags(unittest.TestCase):
    """Whether registered native runs load what an interactive session
    loads is derived from each launch's own argv (#4092), soundly by
    construction (#4156): a launch is shown to pass a flag only where the
    flag is a literal element of the argv list it hands over, unchanged."""

    def _rows(self, files: dict) -> dict:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            for rel, text in files.items():
                _write(root / rel, text)
            parsed = _parsed(root, "notes")
            controllers = {p.relative_to(root).as_posix(): p for p in parsed}
            rows = scan.launch_flags(controllers, parsed)
        return {r["site"].split(":")[0].rsplit("/", 1)[-1]: r for r in rows}

    def _launches(self, files: dict) -> dict:
        return {name: row["carries"] for name, row in self._rows(files).items()}

    #: One launch per file. Shown: a flag literal in the list a function
    #: returns, hands to a call made as a statement or a `with` item, or binds
    #: to a name, before every other use of it in its block, that it
    #: otherwise only hands on whole or reads (#4166). Not shown: a flag a
    #: starred element would bring (a constant, an imported constant, a
    #: comprehension, a record field, a sum), a list handed to a call whose
    #: value is kept, a launch flag outside a list (#4156).
    FLAGS = {"notes/x/flags.py": "SAFE = ['--print', '--safe-mode']\nPLAIN = ['--print']\n",
             "notes/x/a_literal.py": "def go(exe, p):\n    return [exe, '--safe-mode', '--system-prompt', p]\n",
             "notes/x/b_constant.py": "CLI_FLAGS = ['--print', '--safe-mode']\n"
                                      "def go(exe, p):\n    return [exe, *CLI_FLAGS, '--system-prompt', p]\n",
             "notes/x/c_imported.py": "import flags\n"
                                      "def go(exe, p):\n    return [exe, *flags.PLAIN, '--system-prompt', p]\n",
             "notes/x/d_from.py": "from flags import SAFE\n"
                                  "def go(exe, p):\n    return [exe, *SAFE, '--system-prompt', p]\n",
             "notes/x/e_filtered.py": "def go(exe, p, rec):\n    return [exe, *[f for f in rec['cli_flags'] "
                                      "if f != '--safe-mode'], '--system-prompt', p]\n",
             "notes/x/f_field.py": "def go(exe, p, rec):\n    return [exe, *rec['cli_flags'], '--system-prompt', p]\n",
             "notes/x/g_sum.py": "BASE = ['--print']\n"
                                 "def go(exe, p):\n    return [exe, *(BASE + ['--bare']), '--system-prompt', p]\n",
             "notes/x/h_none.py": "def go(exe, p):\n    return [exe, '--print', '--system-prompt', p]\n",
             "notes/x/i_append.py": "def go(exe, p):\n    argv = [exe, '--safe-mode']\n"
                                    "    argv.append('--system-prompt')\n    return argv + [p]\n",
             "notes/x/j_bare.py": "def go(exe, p):\n    return [exe, '--bare', '--system-prompt', p]\n",
             "notes/x/k_statement.py": "import subprocess\ndef go(exe, p):\n"
                                       "    subprocess.run([exe, '--safe-mode', '--system-prompt', p], check=True)\n",
             "notes/x/l_with.py": "import subprocess\ndef go(exe, p):\n"
                                  "    with subprocess.Popen([exe, '--safe-mode', '--system-prompt', p]) as proc:\n"
                                  "        return proc.wait()\n",
             "notes/x/m_kept.py": "import subprocess\ndef go(exe, p):\n"
                                  "    proc = subprocess.Popen([exe, '--safe-mode', '--system-prompt', p])\n"
                                  "    return proc.wait()\n",
             "notes/x/n_held.py": "def go(exe, p):\n    argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                  "    if '--safe-mode' not in argv:\n        raise ValueError(f'unsafe {argv}')\n"
                                  "    return run(argv, timeout=1)\n",
             "notes/x/o_keyword.py": "import subprocess\ndef go(exe, p):\n"
                                     "    argv = (exe, '--safe-mode', '--system-prompt', p)\n"
                                     "    return subprocess.run(args=argv)\n",
             "notes/x/p_yielded.py": "def go(exe, p):\n    yield [exe, '--safe-mode', '--system-prompt', p]\n",
             "notes/x/writer.py": "def make():\n    return {'cli_flags': ['--print', '--safe-mode']}\n"}

    def test_a_flag_is_shown_only_as_a_literal_of_the_list_handed_over(self):
        """`carries` is `--safe-mode` itself, True only where the literal is
        an element of the argv list the launch hands over as built: a flag a
        starred element would bring (a constant, an imported one, a record
        field whoever writes it, a sum) is never followed, a list handed to
        a call whose value is kept may be what that call rebuilds, and
        `--bare` alone (j_bare) does not switch the command, agent and skill
        descriptions off (#4131, #4156)."""
        rows = self._rows(self.FLAGS)
        self.assertEqual({n: r["carries"] for n, r in rows.items()},
                         {"a_literal.py": True, "b_constant.py": None, "c_imported.py": None, "d_from.py": None,
                          "e_filtered.py": None, "f_field.py": None, "g_sum.py": None, "h_none.py": False,
                          "i_append.py": None, "j_bare.py": False, "k_statement.py": True, "l_with.py": True,
                          "m_kept.py": None, "n_held.py": True, "o_keyword.py": True, "p_yielded.py": True})
        self.assertEqual({n: rows[n]["memory_off"] for n in ("a_literal.py", "g_sum.py", "h_none.py", "j_bare.py")},
                         {"a_literal.py": True, "g_sum.py": None, "h_none.py": False, "j_bare.py": True})
        for name, spread in (("b_constant.py", "`*CLI_FLAGS`"), ("c_imported.py", "`*flags.PLAIN`"),
                             ("d_from.py", "`*SAFE`"), ("f_field.py", "`*rec['cli_flags']`"),
                             ("g_sum.py", "`*(BASE + ['--bare'])`")):
            with self.subTest(launch=name):
                self.assertTrue(any(spread in e and "are not followed" in e for e in rows[name]["evidence"]),
                                rows[name]["evidence"])
        self.assertTrue(any("whose value is kept" in e for e in rows["m_kept.py"]["evidence"]), rows["m_kept.py"])
        self.assertTrue(any("is not in an argv list" in e for e in rows["i_append.py"]["evidence"]))
        self.assertIn("notes/x/n_held.py:2 --safe-mode", rows["n_held.py"]["evidence"])

    #: One launch whose argv is bound to a name and handed on whole, shown;
    #: with each edit, another use of that name, not shown, with the words
    #: its reason uses (#4156).
    HOLDER = "def go(exe, p):\n    argv = [exe, '--safe-mode', '--system-prompt', p]\n{edit}    return run(argv)\n"
    HOLDER_EDITS = {
        "remove": ("    argv.remove('--safe-mode')\n", "`argv` is the object of `.remove()`"),
        "pop": ("    argv.pop(1)\n", "`argv` is the object of `.pop()`"),
        "clear": ("    argv.clear()\n", "`argv` is the object of `.clear()`"),
        "extend": ("    argv.extend(['--verbose'])\n", "`argv` is the object of `.extend()`"),
        "del item": ("    del argv[1]\n", "`argv` is subscripted"),
        "item": ("    argv[1] = '--verbose'\n", "`argv` is subscripted"),
        "slice": ("    argv[1:2] = []\n", "`argv` is subscripted"),
        "augmented": ("    argv += ['--verbose']\n", "`argv` is assigned again"),
        "reassigned": ("    argv = argv[2:]\n", "`argv` is assigned again"),
        "alias": ("    flags = argv\n    flags.remove('--safe-mode')\n", "`argv` is bound to another name"),
        "starred": ("    cmd = [*argv]\n", "`argv` is a starred element"),
        "concatenated": ("    cmd = argv + []\n", "`argv` is an operand of `+`"),
        "loop": ("    for argv in [argv]:\n        pass\n", "`argv` is assigned again"),
        "with": ("    with open(p) as argv:\n        pass\n", "`argv` is assigned again"),
        "walrus": ("    (argv := [])\n", "`argv` is assigned again"),
        "deleted": ("    del argv\n", "`argv` is deleted"),
        "except": ("    try:\n        pass\n    except ValueError as argv:\n        pass\n",
                   "`argv` is bound by `except ... as`"),
        "import": ("    import argv\n", "`argv` is bound by an import"),
        "closure": ("    def cb():\n        argv.clear()\n", "`argv` is the object of `.clear()`"),
        "nonlocal": ("    def cb():\n        nonlocal argv\n        argv = []\n", "`argv` is declared `nonlocal`"),
        "nested parameter": ("    def cb(argv):\n        return argv\n", "`argv` is a parameter of a nested function"),
        "match": ("    match p:\n        case [*argv]:\n            pass\n", "`argv` is bound by a `match` pattern"),
    }

    def test_any_other_use_of_the_name_that_holds_the_argv_is_not_shown(self):
        """Codex's reproduction of #4156 removed `--safe-mode` from an argv
        whose binding no listed removal form was read on. Now the name an
        argv list is bound to must be handed on whole (a call's argument, a
        returned value) or only read (a comparison, an f-string); any other
        use, whatever its form, leaves the launch not shown, and so does a
        `global` declaration."""
        self.assertTrue(self._launches({"notes/x/go.py": self.HOLDER.format(edit="")})["go.py"])
        for kind, (edit, words) in self.HOLDER_EDITS.items():
            with self.subTest(edit=kind):
                row = self._rows({"notes/x/go.py": self.HOLDER.format(edit=edit)})["go.py"]
                self.assertIsNone(row["carries"])
                self.assertIsNone(row["memory_off"])
                self.assertTrue(any(words in e for e in row["evidence"]), row["evidence"])
        row = self._rows({"notes/x/go.py": "def go(exe, p):\n    global argv\n"
                                           "    argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                           "    return run(argv)\n"})["go.py"]
        self.assertIsNone(row["carries"])
        self.assertTrue(any("`argv` is declared `global`" in e for e in row["evidence"]), row["evidence"])

    #: The argv list built or bound any other way than as the value handed
    #: over, each with the words its reason uses (#4156).
    CONSTRUCTIONS = {
        "concatenated": ("def go(exe, p):\n    argv = [exe, '--safe-mode', '--system-prompt', p] + []\n"
                         "    return run(argv)\n", "the argv list is an operand of `+`"),
        "concatenated, then removed": ("def go(exe, p):\n    argv = [exe, '--safe-mode', '--system-prompt', p] + []\n"
                                       "    argv.remove('--safe-mode')\n    return run(argv)\n",
                                       "the argv list is an operand of `+`"),
        "wrapped": ("def go(exe, p):\n    argv = list([exe, '--safe-mode', '--system-prompt', p])\n"
                    "    return run(argv)\n", "the argv list is passed to `list`, whose value is kept"),
        "wrapped in the launch": ("def go(exe, p):\n    run(list([exe, '--safe-mode', '--system-prompt', p]))\n",
                                  "the argv list is passed to `list`, whose value is kept"),
        "comprehension": ("def go(exe, p):\n    argv = [a for a in [exe, '--safe-mode', '--system-prompt', p]]\n"
                          "    return run(argv)\n", "the argv list is iterated by a comprehension"),
        "starred": ("def go(exe, p):\n    argv = [*[exe, '--safe-mode', '--system-prompt', p]]\n"
                    "    return run(argv)\n", "the argv list is a starred element"),
        "conditional": ("def go(exe, p):\n    argv = [exe, '--safe-mode', '--system-prompt', p] if p else []\n"
                        "    return run(argv)\n", "the argv list is a branch of a conditional expression"),
        "or": ("def go(exe, p):\n    argv = [exe, '--safe-mode', '--system-prompt', p] or []\n"
               "    return run(argv)\n", "the argv list is an operand of `or`"),
        "augmented": ("def go(exe, p):\n    argv = [exe]\n    argv += ['--safe-mode', '--system-prompt', p]\n"
                      "    return run(argv)\n", "the argv list is the value of an augmented assignment"),
        "chained": ("def go(exe, p):\n    argv = cmd = [exe, '--safe-mode', '--system-prompt', p]\n"
                    "    return run(argv)\n", "the argv list is bound to 2 targets at once"),
        "unpacked": ("def go(exe, p):\n    argv, env = [exe, '--safe-mode', '--system-prompt', p], {}\n"
                     "    return run(argv, env)\n", "the argv list is an element of a tuple"),
        "walrus": ("def go(exe, p):\n    return run(argv := [exe, '--safe-mode', '--system-prompt', p])\n",
                   "the argv list is bound by `:=`"),
        "yield from": ("def go(exe, p):\n    yield from [exe, '--safe-mode', '--system-prompt', p]\n",
                       "the argv list is handed on element by element by `yield from`"),
        "deep holder": ("class L:\n    def go(self, exe, p):\n"
                        "        self.cfg.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                        "        return run(self.cfg.argv)\n", "which cannot be resolved"),
        "module": ("ARGV = ['claude', '--safe-mode', '--system-prompt', 'x']\ndef go():\n    return run(ARGV)\n",
                   "is bound at module level"),
        "class body": ("def go(p):\n    class Job:\n        argv = ['claude', '--safe-mode', '--system-prompt', p]\n"
                       "    return run(Job.argv)\n", "is bound in a class body"),
    }

    def test_an_argv_list_built_any_other_way_is_not_shown(self):
        """Codex's reproduction of #4156 bound an argv concatenated with
        `[]`. The list a launch hands over is shown only where it is a
        call's argument itself (in a call whose value nothing keeps), a
        returned value, or the whole value of a plain or annotated
        assignment, in a function, to a name, attribute or literal-key
        item. A concatenation (with a later removal or without one), a value
        wrapped in a call, a comprehension, a starred element, a
        conditional, an `or`, an augmented assignment, several targets,
        unpacking, `:=`, `yield from` (which hands on the elements), a
        holder that cannot be resolved, and a holder at module or class
        level are not shown."""
        for kind, (source, words) in self.CONSTRUCTIONS.items():
            with self.subTest(construction=kind):
                row = self._rows({"notes/x/go.py": source})["go.py"]
                self.assertIsNone(row["carries"])
                self.assertIsNone(row["memory_off"])
                self.assertTrue(any(words in e for e in row["evidence"]), row["evidence"])

    def test_codex_reproduction_and_a_concatenation_are_not_shown(self):
        """Codex's reproduction of #4156: the audit continuation's argv
        initializer that ends at native.py:787 concatenated with `[]`, then
        `--safe-mode` removed. Discovery read it as carrying the flag, the
        report said every registered launch passes it, and CLAUDE.md stayed
        out of run_controllers. Under the sound rule it is not shown, and so
        is the batch continuation's concatenated with no removal; the native
        canary's launch with its flags inline in the list it hands over is
        shown, and the direct canary's, inline but concatenated, is not."""
        surfaces, facts, texts = _discovered_with_the_round_six_rewrites()
        it = facts["interactive"]
        rows = {x["site"].split(":")[0]: x for x in it["launches"]}
        line = texts[AUDIT_NATIVE][:texts[AUDIT_NATIVE].index("read_text()] + []")].count("\n") + 1
        self.assertEqual(rows[AUDIT_NATIVE]["site"], f"{AUDIT_NATIVE}:{line} --system-prompt")
        for rel in (AUDIT_NATIVE, BATCH_NATIVE, RUN_DIRECT):
            with self.subTest(rel=rel):
                row = rows[rel]
                self.assertIsNone(row["carries"])
                self.assertIsNone(row["memory_off"])
                self.assertTrue(any("the argv list is an operand of `+`" in e for e in row["evidence"]), row)
                self.assertIn(row["site"], it["launches_without_customizations_off"])
        shown = rows[RUN_NATIVE]
        self.assertTrue(shown["carries"] and shown["memory_off"], shown)
        self.assertNotIn(shown["site"], it["launches_without_customizations_off"])
        self.assertEqual(surfaces.files["CLAUDE.md"].roles, dict.fromkeys(SESSION_GATES, "model_facing"))
        statement = scan._session_statement(it)
        self.assertNotIn("does not change a registered run's verdict", statement)
        self.assertIn(f"`{rows[AUDIT_NATIVE]['site']}` cannot be shown to pass `--safe-mode`", statement)

    #: Holders whose binding a use may not see, each with the start of every
    #: reason it must give (#4166): Codex's reproduction (a parameter the
    #: function rebinds only when `enabled`); a parameter rebound first; an
    #: existing attribute or item rebound conditionally, also used through
    #: the name that holds it, or used before its binding; a binding in a
    #: loop, `try`, `with` or `match` body the use does not share; a use
    #: earlier in the loop body that holds the binding.
    UNPRECEDED = {
        "codex": ("import subprocess\n" + CODEX_GO,
                  ["notes/x/go.py:4 `argv` is a parameter of `go()`",
                   "notes/x/go.py:5 `argv` is used outside the block that holds the binding at line 4"]),
        "parameter": ("def go(exe, p, argv):\n    argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                      "    return run(argv)\n", ["notes/x/go.py:2 `argv` is a parameter of `go()`"]),
        "attribute": ("class Launch:\n    def go(self, exe, p, enabled):\n        if enabled:\n"
                      "            self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                      "        return run(self.argv)\n",
                      ["notes/x/go.py:5 `self.argv` is used outside the block that holds the binding at line 4"]),
        "item": ("def go(exe, p, job, enabled):\n    if enabled:\n"
                 "        job['argv'] = [exe, '--safe-mode', '--system-prompt', p]\n    return run(job['argv'])\n",
                 ["notes/x/go.py:4 `job['argv']` is used outside the block that holds the binding at line 3"]),
        "item through its holder": ("def go(exe, p, job, enabled):\n    if enabled:\n"
                                    "        job['argv'] = [exe, '--safe-mode', '--system-prompt', p]\n"
                                    "    return execute(job)\n",
                                    ["notes/x/go.py:4 `job`, which holds the argv, is used outside the block that "
                                     "holds the binding at line 3"]),
        "attribute used first": ("class Launch:\n    def go(self, exe, p):\n        run(self.argv)\n"
                                 "        self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                 "        return run(self.argv)\n",
                                 ["notes/x/go.py:3 `self.argv` is used before the binding at line 4"]),
        "loop": ("def go(exe, p, jobs):\n    for job in jobs:\n"
                 "        argv = [exe, '--safe-mode', '--system-prompt', p]\n    return run(argv)\n",
                 ["notes/x/go.py:4 `argv` is used outside the block that holds the binding at line 3"]),
        "earlier in the loop": ("def go(exe, p, jobs):\n    for job in jobs:\n        if job:\n            run(argv)\n"
                                "        argv = [exe, '--safe-mode', '--system-prompt', p]\n",
                                ["notes/x/go.py:4 `argv` is used before the binding at line 5"]),
        "try": ("def go(exe, p):\n    try:\n        argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                "    except ValueError:\n        pass\n    return run(argv)\n",
                ["notes/x/go.py:6 `argv` is used outside the block that holds the binding at line 3"]),
        "with": ("def go(exe, p, lock):\n    with lock:\n        argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                 "    return run(argv)\n",
                 ["notes/x/go.py:4 `argv` is used outside the block that holds the binding at line 3"]),
        "match": ("def go(exe, p, kind):\n    match kind:\n        case 'audit':\n"
                  "            argv = [exe, '--safe-mode', '--system-prompt', p]\n    return run(argv)\n",
                  ["notes/x/go.py:5 `argv` is used outside the block that holds the binding at line 4"]),
    }

    def test_a_holder_is_not_shown_where_a_use_may_not_see_its_binding(self):
        """Codex's reproduction of #4166: `go(argv, enabled)` rebinds its
        parameter to a list holding `--safe-mode` only when `enabled`, then
        launches `argv`, so `go(['claude', '--system-prompt', 'text'],
        False)` launches without the flag; it read as carrying it. A holder
        is now shown only where its one binding comes before every other use
        of it in the same statement list, and a name holder is not a
        parameter. Each case here read as carrying the flag before."""
        for kind, (source, reasons) in self.UNPRECEDED.items():
            with self.subTest(holder=kind):
                row = self._rows({"notes/x/go.py": source})["go.py"]
                self.assertIsNone(row["carries"])
                self.assertIsNone(row["memory_off"])
                for words in reasons:
                    self.assertTrue(any(e.startswith(words) for e in row["evidence"]), (words, row["evidence"]))

    #: The same holders bound before every use in their own block: the use
    #: in that block, or nested in a later statement of it, the way each
    #: registered launch hands its argv to a call inside a later `with` or
    #: `try` (#4166).
    PRECEDED = {
        "with": ("def go(exe, p, lock):\n    with lock:\n        argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                 "        return run(argv)\n"),
        "if": ("def go(exe, p, enabled):\n    if enabled:\n        argv = [exe, '--safe-mode', '--system-prompt', p]\n"
               "        return run(argv)\n"),
        "loop": ("def go(exe, p, jobs):\n    for job in jobs:\n        argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                 "        run(argv)\n"),
        "nested later": ("def go(exe, p, proxy):\n    argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                         "    with proxy.running():\n        try:\n            return run(argv)\n        finally:\n"
                         "            proxy.close()\n"),
        "attribute": ("class Launch:\n    def go(self, exe, p, enabled):\n        if enabled:\n"
                      "            self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                      "            return run(self.argv)\n"),
        "item": ("def go(exe, p, job):\n    job['argv'] = [exe, '--safe-mode', '--system-prompt', p]\n"
                 "    if job is not None:\n        return execute(job)\n"),
    }

    def test_a_holder_bound_before_every_use_in_its_block_is_shown(self):
        """Where the binding runs on every path to each use, in its own block
        or nested in a later statement of it, the holder is shown (#4166):
        the rule refuses what may not see the binding, not the shape of the
        registered launches."""
        for kind, source in self.PRECEDED.items():
            with self.subTest(holder=kind):
                row = self._rows({"notes/x/go.py": source})["go.py"]
                self.assertTrue(row["carries"], row["evidence"])
                self.assertTrue(row["memory_off"], row["memory_evidence"])

    def test_codex_conditional_argv_keeps_the_session_surfaces_in_run_controllers(self):
        """Codex's reproduction of #4166 through discovery: with every
        registered launch shown to pass `--safe-mode` (each writes it as a
        literal of the argv list it hands over), Codex's `go(argv, enabled)`
        in a controller read as carrying the flag, so the report said
        registered runs are unaffected and CLAUDE.md left run_controllers.
        Now `go` is not shown and CLAUDE.md stays a run_controllers surface,
        while the four registered launches, whose argv a later `with` or
        `try` hands on, are still shown."""
        surfaces, facts, texts = _discovered_with_the_round_seven_rewrites()
        it = facts["interactive"]
        rows = {x["site"].split(":")[0]: x for x in it["launches"]}
        self.assertEqual(set(rows), {AUDIT_NATIVE, BATCH_NATIVE, RUN_NATIVE, RUN_DIRECT, AUDIT_PREPARE})
        for rel in (AUDIT_NATIVE, BATCH_NATIVE, RUN_NATIVE, RUN_DIRECT):
            with self.subTest(rel=rel):
                self.assertTrue(rows[rel]["carries"] and rows[rel]["memory_off"], rows[rel])
        text = texts[AUDIT_PREPARE]
        bound = text[:text.index(CODEX_GO)].count("\n") + 3
        go = rows[AUDIT_PREPARE]
        self.assertEqual(go["site"], f"{AUDIT_PREPARE}:{bound} --system-prompt")
        self.assertIsNone(go["carries"])
        self.assertIsNone(go["memory_off"])
        self.assertIn(f"{AUDIT_PREPARE}:{bound} `argv` is a parameter of `go()`, which holds the caller's list "
                      "until the binding runs", go["evidence"])
        self.assertIn(f"{AUDIT_PREPARE}:{bound + 1} `argv` is used outside the block that holds the binding at "
                      f"line {bound}, which may not have run there", go["evidence"])
        self.assertEqual(it["launches_without_customizations_off"], [go["site"]])
        self.assertEqual(it["launches_without_memory_off"], [go["site"]])
        self.assertEqual(surfaces.files["CLAUDE.md"].roles, dict.fromkeys(SESSION_GATES, "model_facing"))
        statement = scan._session_statement(it)
        self.assertNotIn("does not change a registered run's verdict", statement)
        self.assertIn(f"`{go['site']}` cannot be shown to pass `--safe-mode`", statement)

    #: An argv bound by an annotated assignment, held by an attribute or by an
    #: item, then shortened in the function that builds it, each beside the
    #: same launch left whole (#4142), with the words its reason uses (#4156).
    HELD_SHORTENED = {
        "notes/x/v_annotated.py": "def go(exe, p):\n    argv: list[str] = [exe, '--safe-mode', '--system-prompt', p]\n"
                                  "    argv.remove('--safe-mode')\n    return argv\n",
        "notes/x/w_annotated_again.py": "def go(exe, p):\n    argv: list[str] = [exe, '--safe-mode', '--system-prompt', p]\n"
                                        "    argv = argv[2:]\n    return argv\n",
        "notes/x/x_annotated_module.py": "ARGV: list = ['claude', '--safe-mode', '--system-prompt', 'x']\n"
                                         "ARGV.remove('--safe-mode')\n",
        "notes/x/y_attribute.py": "class Launch:\n    def go(self, exe, p):\n"
                                  "        self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                  "        self.argv.remove('--safe-mode')\n        return self.argv\n",
        "notes/x/z_attribute_again.py": "class Launch:\n    def go(self, exe, p):\n"
                                        "        self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                        "        self.argv = self.argv[2:]\n        return self.argv\n",
        "notes/x/za_item.py": "def go(exe, p, job):\n    job['argv'] = [exe, '--safe-mode', '--system-prompt', p]\n"
                              "    del job['argv'][1]\n    return job\n",
        "notes/x/zb_annotated_attribute.py": "class Launch:\n    def go(self, exe, p):\n"
                                             "        self.argv: list = [exe, '--safe-mode', '--system-prompt', p]\n"
                                             "        self.argv.pop(1)\n        return self.argv\n"}
    HELD_REASONS = {"v_annotated.py": "`argv` is the object of `.remove()`",
                    "w_annotated_again.py": "`argv` is assigned again",
                    "x_annotated_module.py": "is bound at module level",
                    "y_attribute.py": "`self.argv` is the object of `.remove()`",
                    "z_attribute_again.py": "`self.argv` is assigned again",
                    "za_item.py": "`job['argv']` is subscripted",
                    "zb_annotated_attribute.py": "`self.argv` is the object of `.pop()`"}
    HELD_INTACT = {
        "notes/x/v_annotated.py": "def go(exe, p):\n    argv: list[str] = [exe, '--safe-mode', '--system-prompt', p]\n"
                                  "    return argv\n",
        "notes/x/w_annotated_again.py": "def go(exe, p):\n    argv: list[str] = [exe, '--safe-mode', '--system-prompt', p]\n"
                                        "    return argv\n",
        "notes/x/x_annotated_module.py": "ARGV: list = ['claude', '--safe-mode', '--system-prompt', 'x']\n",
        "notes/x/y_attribute.py": "class Launch:\n    def go(self, exe, p):\n"
                                  "        self.argv = [exe, '--safe-mode', '--system-prompt', p]\n        return self.argv\n",
        "notes/x/z_attribute_again.py": "class Launch:\n    def go(self, exe, p):\n"
                                        "        self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                        "        return self.argv\n",
        "notes/x/za_item.py": "def go(exe, p, job):\n    job['argv'] = [exe, '--safe-mode', '--system-prompt', p]\n"
                              "    return job\n",
        "notes/x/zb_annotated_attribute.py": "class Launch:\n    def go(self, exe, p):\n"
                                             "        self.argv: list = [exe, '--safe-mode', '--system-prompt', p]\n"
                                             "        return self.argv\n"}

    def test_an_annotated_attribute_or_item_argv_is_read_for_changes(self):
        """`argv: list[str] = [...]` is read like `argv = [...]`, and an argv
        held by an attribute or an item (`self.argv`, `job['argv']`) is held
        to the same rule as a name, and so is the name that holds it (#4142,
        #4156). A module-level argv is not shown even left whole: every
        module that imports it can change it."""
        shortened = self._rows(self.HELD_SHORTENED)
        self.assertEqual({n: r["carries"] for n, r in shortened.items()}, dict.fromkeys(self.HELD_REASONS))
        for name, words in self.HELD_REASONS.items():
            with self.subTest(launch=name):
                self.assertTrue(any(words in e for e in shortened[name]["evidence"]), shortened[name]["evidence"])
        self.assertEqual(self._launches(self.HELD_INTACT),
                         {**dict.fromkeys(self.HELD_REASONS, True), "x_annotated_module.py": None})
        base = self._rows({"notes/x/za_item.py": "def go(exe, p, job):\n"
                                                 "    job['argv'] = [exe, '--safe-mode', '--system-prompt', p]\n"
                                                 "    job.update(argv=[exe])\n    return job\n",
                           "notes/x/y_attribute.py": "class Launch:\n    def go(self, exe, p):\n"
                                                     "        self.argv = [exe, '--safe-mode', '--system-prompt', p]\n"
                                                     "        self.reset()\n        return self.argv\n"})
        for name, words in (("za_item.py", "`job`, which holds the argv, is the object of `.update()`"),
                            ("y_attribute.py", "`self`, which holds the argv, is the object of `.reset()`")):
            with self.subTest(base=name):
                self.assertIsNone(base[name]["carries"])
                self.assertTrue(any(words in e for e in base[name]["evidence"]), base[name]["evidence"])

    def test_a_registered_launch_whose_annotated_argv_is_shortened_is_not_shown(self):
        """The reviewer's rewrite of the audit continuation (#4142): bound by
        an annotated assignment and then shortened, its argv is not shown to
        pass `--safe-mode`; the removal is named beside the starred
        `*CLI_FLAGS` the sound rule never follows (#4156)."""
        surfaces, facts, texts = _discovered_with_the_round_five_rewrites()
        text = texts[AUDIT_NATIVE]
        line = text[:text.index(AUDIT_ARGV_END)].count("\n") + 1
        site = f"{AUDIT_NATIVE}:{line} --system-prompt"
        self.assertIn(site, facts["interactive"]["launches_without_customizations_off"])
        row = next(x for x in facts["interactive"]["launches"] if x["site"] == site)
        self.assertIsNone(row["carries"])
        self.assertTrue(any("`argv` is the object of `.remove()`" in e for e in row["evidence"]), row)
        self.assertTrue(any("`*CLI_FLAGS`" in e for e in row["evidence"]), row)
        self.assertEqual(surfaces.files["CLAUDE.md"].roles, dict.fromkeys(SESSION_GATES, "model_facing"))
        self.assertNotIn("does not change a registered run's verdict", scan._session_statement(facts["interactive"]))

    def test_a_system_prompt_file_launch_is_a_launch(self):
        """`--system-prompt-file` and `--append-system-prompt-file` launch a
        native runtime as surely as `--system-prompt` (#4131), and so does a
        flag spelled with its value (`--system-prompt=...`)."""
        rows = self._rows({"notes/x/file_safe.py": "def go(exe, path):\n    return [exe, '--safe-mode', "
                                                   "'--system-prompt-file', path]\n",
                           "notes/x/file_plain.py": "def go(exe, path):\n    return [exe, '--print', "
                                                    "'--append-system-prompt-file', path]\n",
                           "notes/x/equals.py": "def go(exe, p):\n    return [exe, '--print', f'--system-prompt={p}']\n"})
        self.assertEqual({n: r["carries"] for n, r in rows.items()},
                         {"file_safe.py": True, "file_plain.py": False, "equals.py": False})
        self.assertTrue(rows["file_safe.py"]["site"].endswith("--system-prompt-file"))
        self.assertTrue(rows["file_plain.py"]["site"].endswith("--append-system-prompt-file"))

    def test_bare_switches_off_the_memory_and_the_hooks_but_not_the_descriptions(self):
        """`claude --help`: `--bare` skips the hooks and CLAUDE.md, "Skills
        still resolve via /skill-name" (#4131). A run launched with `--bare`
        alone loads the command, agent and skill descriptions, so those, and
        not CLAUDE.md, are its surfaces too."""
        text = scan._session_statement({"launches": [BARE_LAUNCH]})
        self.assertNotIn("does not change a registered run's verdict", text)
        self.assertIn("it passes `--bare`", text)
        surfaces, facts = _discovered_with_a_bare_launch()
        self.assertEqual(facts["interactive"]["launches_without_customizations_off"], [BARE_LAUNCH["site"]])
        self.assertEqual(facts["interactive"]["launches_without_memory_off"], [])
        self.assertEqual(surfaces.files["CLAUDE.md"].roles, {"interactive_session": "model_facing"})
        self.assertNotIn("run_controllers", surfaces.files[".claude/settings.json"].roles)
        review = surfaces.files[".claude/agents/d4d-review-record.md"]
        self.assertEqual(review.roles.get("run_controllers"), "exposed")
        self.assertEqual(review.loaded["run_controllers"], review.loaded["interactive_session"])

    def test_where_every_launch_is_shown_the_session_is_interactive_only(self):
        """Where every registered native launch is shown to pass
        `--safe-mode`, no session surface is a run_controllers surface and
        the report says registered runs are unaffected (#4156)."""
        surfaces, facts = _discovered_with_every_launch_shown()
        it = facts["interactive"]
        self.assertEqual(it["launches_without_customizations_off"], [])
        self.assertEqual(it["launches_without_memory_off"], [])
        for rel in ("CLAUDE.md", ".claude/settings.json", ".claude/agents/d4d-review-record.md"):
            with self.subTest(rel=rel):
                self.assertNotIn("run_controllers", surfaces.files[rel].roles)
        self.assertIn("does not change a registered run's verdict", scan._session_statement(it))

    def test_the_report_says_unaffected_only_when_every_launch_carries_the_flag(self):
        ok = {"site": "a.py:1 --system-prompt", "carries": True, "evidence": ["b.py:2 --safe-mode"]}
        bad = {"site": "c.py:3 --system-prompt", "carries": False, "evidence": ["no element holds --safe-mode"]}
        unknown = {"site": "d.py:4 --system-prompt", "carries": None, "evidence": ["d.py:4 `x` is computed"]}
        self.assertIn("does not change a registered run's verdict", scan._session_statement({"launches": [ok]}))
        for rows in ([ok, bad], [ok, unknown], [bad]):
            text = scan._session_statement({"launches": rows})
            with self.subTest(rows=[r["site"] for r in rows]):
                self.assertNotIn("does not change a registered run's verdict", text)
                for r in rows:
                    if not r["carries"]:
                        self.assertIn(r["site"], text)

    def test_a_launch_without_the_flag_makes_the_session_surfaces_run_controllers(self):
        """A registered run so launched loads CLAUDE.md and the session
        descriptions, so their violations count in run_controllers too."""
        surfaces, facts = _discovered_with_a_loading_workflow_and_an_unsafe_launch()
        self.assertEqual(facts["interactive"]["launches_without_customizations_off"], [UNSAFE_LAUNCH["site"]])
        claude = surfaces.files["CLAUDE.md"]
        self.assertEqual(claude.roles, {"interactive_session": "model_facing", "run_controllers": "model_facing"})
        review = surfaces.files[".claude/agents/d4d-review-record.md"]
        self.assertEqual(review.loaded["run_controllers"], review.loaded["interactive_session"])
        planted, _ = _plant("CLAUDE.md", "Always describe the dataset as AI-READI.", surface=claude)
        self.assertTrue(planted)
        self.assertTrue(all(h["gates_in"] == ["interactive_session", "run_controllers"] for h in planted))


class TestConstantText(unittest.TestCase):
    """A module constant a model receives is model text, and so is all it is
    built from, followed recursively and each constant once (#4156)."""

    def test_codex_reproduction_a_sentence_in_a_constant_system_is_built_from_gates(self):
        """Codex's reproduction: in the audit preparer, `POLICY = 'You must
        use CHORUS data.'` and `SYSTEM = POLICY + <the existing literal>`.
        `render_system()` returns that text, yet the CHORUS hit was neither
        model-facing nor gating; now it is a run_controllers violation."""
        surfaces, _, texts = _discovered_with_the_round_six_rewrites()
        text = texts[AUDIT_PREPARE]
        line = text[:text.index("'You must use CHORUS data.'")].count("\n") + 1
        hits = [h for h in _scan_text(AUDIT_PREPARE, text, surfaces.files[AUDIT_PREPARE])
                if h["match"] == "CHORUS" and h["line"] == line]
        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0]["model_facing"] and hits[0]["violation"], hits)
        self.assertEqual(hits[0]["gates_in"], ["run_controllers"])
        self.assertTrue(hits[0]["model_text_function"].startswith("POLICY (part of SYSTEM"), hits)

    #: A controller whose `render_system()` returns a constant built from
    #: other constants, a function, a constant imported by name, every kind
    #: of write (plain, augmented, annotated, an item assignment, a method
    #: call) and a cycle, beside a constant nothing builds the text from.
    PROMPTS = ("from base import SHARED\n"                     # 1
               "def tail():\n"                                 # 2
               "    return 'Tail text.'\n"                     # 3
               "POLICY = 'Policy text.'\n"                     # 4
               "BODY = POLICY + ' Body text.'\n"               # 5
               "SYSTEM = BODY + SHARED + tail()\n"             # 6
               "SYSTEM += ' Appended text.'\n"                 # 7
               "PARTS = ['Part one.']\n"                       # 8
               "PARTS.append('Part two.')\n"                   # 9
               "TABLE: dict = {'a': 'Table text.'}\n"          # 10
               "TABLE['b'] = 'More table text.'\n"             # 11
               "CYCLE_A = 'Cycle a.'\n"                        # 12
               "CYCLE_B = CYCLE_A + ' b.'\n"                   # 13
               "CYCLE_A = CYCLE_B + ' again.'\n"               # 14
               "UNRELATED = 'Not model text.'\n"               # 15
               "def render_system():\n"                        # 16
               "    return SYSTEM + ' '.join(PARTS) + TABLE['b'] + CYCLE_A\n")  # 17

    def test_the_constants_a_model_text_constant_is_built_from_are_model_text(self):
        """Every statement at the top of the module that writes a marked
        constant (`=`, `+=`, an annotated assignment, an item assignment, a
        method call on it) is model text, and so is what it is built from:
        the constants it names, of its module or imported by name,
        recursively, the functions whose results become part of it; a cycle
        ends; a constant nothing builds the text from is not marked."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes/exp_4156c"
            _write(base / "launch.py", "from data_sheets_schema.api_runner import RunSpec\nimport prompts\n"
                                       "spec = RunSpec\n")
            _write(base / "prompts.py", self.PROMPTS)
            _write(base / "base.py", "SHARED = 'Shared text.'\nOTHER = 'Not model text either.'\n")
            parsed = _parsed(root, "notes")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            spans = scan.model_text_spans(root, parsed, index, controllers)
        self.assertEqual({(a, b) for a, b, _ in spans["notes/exp_4156c/prompts.py"]},
                         {(2, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12),
                          (13, 13), (14, 14), (16, 17)})
        self.assertEqual({(a, b) for a, b, _ in spans["notes/exp_4156c/base.py"]}, {(1, 1)})

    def _gating_hit(self, match: str, sentence: str) -> dict:
        """The one hit of `match` on the line of `sentence` in the audit
        preparer as the #4166 rewrites leave it, scanned under the role
        discovery gives it."""
        surfaces, _, texts = _discovered_with_the_round_seven_rewrites()
        text = texts[AUDIT_PREPARE]
        line = text[:text.index(sentence)].count("\n") + 1
        hits = [h for h in _scan_text(AUDIT_PREPARE, text, surfaces.files[AUDIT_PREPARE])
                if h["match"] == match and h["line"] == line]
        self.assertEqual(len(hits), 1, hits)
        return hits[0]

    def test_codex_reproduction_a_constant_a_top_level_setdefault_fills_gates(self):
        """Codex's reproduction of #4166, through discovery: `PARTS = {}`,
        `DEFAULT_POLICY = PARTS.setdefault('default', POLICY)` and `SYSTEM`
        built from `PARTS.values()`. The method call sat in an assignment to
        another name, so it was not read as a write of `PARTS`, and the
        CHORUS hit in `POLICY` was neither model-facing nor gating. Now any
        method call on a marked constant, wherever a top-level statement
        makes it, is a write, and its arguments are followed."""
        hit = self._gating_hit("CHORUS", "'You must use CHORUS data.'")
        self.assertTrue(hit["model_facing"] and hit["violation"], hit)
        self.assertEqual(hit["gates_in"], ["run_controllers"])
        self.assertTrue(hit["model_text_function"].startswith("POLICY (part of PARTS, part of SYSTEM"), hit)

    def test_a_constant_an_assigned_append_fills_gates(self):
        """The assigned `append` Codex also reproduced through discovery
        (#4166): `ADDED = LINES.append(RULE)` puts `RULE` in `LINES`, which
        `SYSTEM` joins, so the VOICE hit in `RULE` is model text and gates."""
        hit = self._gating_hit("VOICE", "'Always describe the VOICE cohort.'")
        self.assertTrue(hit["model_facing"] and hit["violation"], hit)
        self.assertEqual(hit["gates_in"], ["run_controllers"])
        self.assertTrue(hit["model_text_function"].startswith("RULE (part of LINES, part of SYSTEM"), hit)

    #: A controller whose `render_system()` joins a constant that method
    #: calls fill wherever a top-level statement makes them (#4166), each
    #: putting in it a constant of its own line, beside a call in a function
    #: body and a call on another object, which are not writes of it.
    METHOD_CALLS = ("POLICY = 'Policy text.'\n"                           # 1
                    "NOTE = 'Argument text.'\n"                           # 2
                    "RULE = 'Condition text.'\n"                          # 3
                    "MORE = 'Block text.'\n"                              # 4
                    "CHAINED = 'Chained text.'\n"                         # 5
                    "LATE = 'Function text.'\n"                           # 6
                    "ELSEWHERE = 'Not model text.'\n"                     # 7
                    "PARTS = {}\n"                                        # 8
                    "DEFAULT = PARTS.setdefault('default', POLICY)\n"     # 9 an assignment's value
                    "print(PARTS.update(note=NOTE))\n"                    # 10 another call's argument
                    "if PARTS.setdefault('rule', RULE):\n"                # 11 a condition
                    "    PARTS.setdefault('more', MORE)\n"                # 12 a block's body
                    "PARTS.setdefault('list', []).append(CHAINED)\n"      # 13 a call on its result
                    "def later():\n"                                      # 14
                    "    PARTS.setdefault('late', LATE)\n"                # 15 a function body: not read
                    "OTHER = {}.setdefault('x', ELSEWHERE)\n"             # 16 another object
                    "def render_system():\n"                              # 17
                    "    return ''.join(PARTS.values())\n")               # 18

    def test_a_method_call_on_a_constant_is_a_write_wherever_a_top_level_statement_makes_it(self):
        """A method call whose receiver holds a marked constant is a write of
        it wherever a top-level statement's code runs on import (#4166): in
        an assignment's value, another call's argument, a condition, a
        block's body, or on the result of another call on it; the constants
        its arguments name are followed in turn. A call in a function body
        and a call on another object are not writes of it (SKILL.md,
        Limits)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes/exp_4166"
            _write(base / "launch.py", "from data_sheets_schema.api_runner import RunSpec\nimport prompts\n"
                                       "spec = RunSpec\n")
            _write(base / "prompts.py", self.METHOD_CALLS)
            parsed = _parsed(root, "notes")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            spans = scan.model_text_spans(root, parsed, index, controllers)
        self.assertEqual({(a, b) for a, b, _ in spans["notes/exp_4166/prompts.py"]},
                         {(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12),
                          (13, 13), (17, 18)})


class TestAssistantInstructions(unittest.TestCase):
    """An assistant instruction file is a surface only where the
    @d4dassistant workflow, a playbook or a loaded instruction loads it
    (#4093)."""

    def test_an_instruction_file_nothing_loads_is_not_a_surface(self):
        surfaces, facts = _discovered()
        edit, create = ".github/workflows/d4d_assistant_edit.md", ".github/workflows/d4d_assistant_create.md"
        self.assertNotIn(edit, surfaces.files)
        self.assertEqual(facts["assistant_instructions"][edit], [])
        self.assertEqual(surfaces.files[create].roles, {"native_agentic": "model_facing"})
        self.assertEqual(facts["assistant_instructions"][create],
                         [".claude/commands/d4d-assistant.md (native_agentic)",
                          ".claude/commands/d4d-webfetch.md (native_agentic)"])
        github = sorted(r for r, s in surfaces.files.items() if "github_assistant" in s.approaches)
        self.assertIn(".github/workflows/d4d-agent.yml", github)
        self.assertFalse([r for r in github if r.startswith(".github/workflows/d4d_assistant_") and r.endswith(".md")])

    def test_an_instruction_file_the_workflow_loads_is_the_assistants(self):
        surfaces, facts = _discovered_with_a_loading_workflow_and_an_unsafe_launch()
        edit = ".github/workflows/d4d_assistant_edit.md"
        self.assertEqual(surfaces.files[edit].roles, {"github_assistant": "model_facing"})
        self.assertIn(".github/workflows/d4d-agent.yml", surfaces.files[edit].why)
        self.assertEqual(facts["assistant_instructions"][edit], [".github/workflows/d4d-agent.yml (github_assistant)"])
        planted, _ = _plant(edit, "When editing a CHORUS datasheet, keep its consortium list.",
                            surface=surfaces.files[edit])
        self.assertTrue(planted and all(h["violation"] and h["gates_in"] == ["github_assistant"] for h in planted))


class TestControllerRuns(unittest.TestCase):
    """A controller module runs as a script only where something runs it: an
    argv, a document beside it, or nothing importing it. An import by
    another controller never runs its __main__ block (#4093)."""

    def test_a_module_runs_as_a_script_only_where_something_runs_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes/exp_4093"
            _write(base / "seed.py", "import sys\nfrom data_sheets_schema.api_runner import RunSpec\n"
                                     "import helper, worker, tool, documented\nspec = RunSpec\n"
                                     "RUN = [sys.executable, '-m', 'tool', '--x']\n")
            _write(base / "helper.py", "X = 1\n")
            _write(base / "worker.py", "import sys\nARGV = [sys.executable, __file__, '--worker']\n")
            _write(base / "tool.py", "Y = 1\n")
            _write(base / "documented.py", "Z = 1\n")
            _write(base / "README.md", "Run it from here:\n\n    python -m documented --label L\n")
            parsed = _parsed(root, "notes")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            runs = scan.controller_run_evidence(root, parsed, index, controllers)
        names = {f"notes/exp_4093/{n}.py" for n in ("seed", "helper", "worker", "tool", "documented")}
        self.assertEqual(set(controllers), names)
        self.assertEqual(set(runs), names - {"notes/exp_4093/helper.py"})
        self.assertIn("an entry point", runs["notes/exp_4093/seed.py"])
        self.assertIn("relaunches itself", runs["notes/exp_4093/worker.py"])
        self.assertIn("-m tool", runs["notes/exp_4093/tool.py"])
        self.assertIn("README.md", runs["notes/exp_4093/documented.py"])

    def test_a_main_block_in_a_module_a_controller_only_imports_does_not_gate(self):
        """transport.py is only imported; bounded_stream.py relaunches
        itself, so its __main__ block runs."""
        surfaces, facts = _discovered()
        demo = 'if __name__ == "__main__":\n    DEMO_PROJECTS_4093 = ["CHORUS"]'
        transport = "notes/matched_cborg_2026-09-13/audit_controls/transport.py"
        self.assertEqual(surfaces.files[transport].runs, set())
        self.assertEqual(facts["controller_runs"][transport], "")
        quiet, _ = _plant(transport, demo)
        chorus = [h for h in quiet if h["match"] == "CHORUS"]
        self.assertTrue(chorus and all(h.get("main_block") and not h["violation"] for h in chorus))
        stream = "notes/matched_cborg_2026-09-13/audit_controls/bounded_stream.py"
        self.assertIn("run_controllers", surfaces.files[stream].runs)
        self.assertIn("relaunches itself", facts["controller_runs"][stream])
        loud, _ = _plant(stream, demo)
        self.assertTrue([h for h in loud if h["match"] == "CHORUS" and h["violation"]])

    def test_a_main_block_that_launches_or_runs_a_cli_makes_its_module_run(self):
        """A module other controllers import runs as a script where its own
        `__main__` block calls a function that launches a run (in it or in a
        module function it calls), or a command-line interface nothing else
        calls (#4130); not where the block does something else, or where
        another module calls the CLI."""
        cli = ("import argparse\ndef parse(argv=None):\n    parser = argparse.ArgumentParser()\n"
               "    return parser.parse_args(argv)\ndef main():\n    return parse()\n"
               "if __name__ == '__main__':\n    main()\n")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes/exp_4130"
            _write(base / "seed.py", "from data_sheets_schema.api_runner import RunSpec\n"
                                     "import launcher, prep, prep_called, plain\nspec = RunSpec\n"
                                     "def again():\n    return prep_called.main()\n")
            _write(base / "launcher.py", "def build(exe, p):\n    return [exe, '--safe-mode', '--system-prompt', p]\n"
                                         "def main():\n    return build('claude', 'x')\n"
                                         "if __name__ == '__main__':\n    raise SystemExit(main())\n")
            _write(base / "prep.py", cli)
            _write(base / "prep_called.py", cli)
            _write(base / "plain.py", "def helper():\n    return 1\nif __name__ == '__main__':\n    print(helper())\n")
            parsed = _parsed(root, "notes")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            runs = scan.controller_run_evidence(root, parsed, index, controllers)
        self.assertEqual(set(controllers), {f"notes/exp_4130/{n}.py" for n in
                                            ("seed", "launcher", "prep", "prep_called", "plain")})
        self.assertIn("launches a run (notes/exp_4130/launcher.py:2 --system-prompt)", runs["notes/exp_4130/launcher.py"])
        self.assertIn("command-line interface nothing else calls", runs["notes/exp_4130/prep.py"])
        self.assertEqual(set(runs), {"notes/exp_4130/seed.py", "notes/exp_4130/launcher.py", "notes/exp_4130/prep.py"})

    def test_the_registered_launchers_run_as_scripts(self):
        """run_native_canary.py and run_api_canary.py launch from main(),
        which only their `__main__` blocks call, and prepare_registration.py
        is an argparse CLI nothing else calls: other controllers import their
        helpers, and each still runs as a script (#4130). A project default
        planted in such a block gates."""
        surfaces, facts = _discovered()
        base = "notes/matched_cborg_2026-09-13/"
        for rel, why in ((base + "native_controls/run_native_canary.py", "launches a run"),
                         (base + "run_api_canary.py", "launches a run (" + base + "run_api_canary.py:"),
                         (base + "prepare_registration.py", "a command-line interface nothing else calls")):
            with self.subTest(rel=rel):
                self.assertIn(why, facts["controller_runs"][rel])
                self.assertIn("run_controllers", surfaces.files[rel].runs)
        for rel in (base + "native_controls/run_native_canary.py", base + "prepare_registration.py"):
            with self.subTest(planted=rel):
                loud, _ = _plant(rel, 'if __name__ == "__main__":\n    DEFAULT_PROJECT_4130 = "CHORUS"')
                self.assertTrue([h for h in loud if h["match"] == "CHORUS" and h["violation"]
                                 and h["gates_in"] == ["run_controllers"]], loud)


class TestHookText(unittest.TestCase):
    """The reason a PreToolUse hook gives for a denial is shown to the model
    it denies (#4130): a registered native run answers every refused tool
    call with `hook_output`'s `permissionDecisionReason`, built from the
    reason a classifier returns."""

    HOOKS = {"function": "def deny(decision, why):\n"
                         "    return {} if decision == 'allowed' else {'hookSpecificOutput': {\n"
                         "        'permissionDecisionReason': 'Refused: ' + why}}\n",
             "method": "class Hook:\n"
                       "    def deny(self, decision, why):\n"
                       "        return {} if decision == 'allowed' else {'permissionDecisionReason': 'Refused: ' + why}\n"}

    def test_a_deny_reason_and_the_classifiers_that_feed_it_are_model_text(self):
        """The hook's own text, and the reason element of every pair whose
        decision the hook tests ('allowed'), widened by the other decisions
        those functions return ('refused'); not a function whose decisions
        are unrelated, nor a message that is not a reason. A method's `self`
        does not shift the pair."""
        for kind, hook in self.HOOKS.items():
            with self.subTest(hook=kind):
                spans = self._hook_spans(hook)
                self.assertEqual({a for a, _, _ in spans["notes/exp_4130h/hook.py"]}, {3})
                self.assertEqual({a for a, _, _ in spans["notes/exp_4130h/policy.py"]}, {3, 4, 6})

    #: The same deny reason set in each of the other ways a field can be
    #: set, with the lines of the hook text each one gives (#4142).
    HOOK_FORMS = {
        "item assignment": ("def deny(decision, why):\n    out = {}\n    if decision != 'allowed':\n"
                            "        out['permissionDecisionReason'] = 'Refused: ' + why\n    return out\n", {4}),
        "annotated item assignment": ("def deny(decision, why):\n    out = {}\n    if decision != 'allowed':\n"
                                      "        out['permissionDecisionReason']: str = 'Refused: ' + why\n"
                                      "    return out\n", {4}),
        "appended": ("def deny(decision, why):\n    out = {'permissionDecisionReason': 'Refused'}\n"
                     "    if decision != 'allowed':\n        out['permissionDecisionReason'] += ': ' + why\n"
                     "    return out\n", {2, 4}),
        "setdefault": ("def deny(decision, why):\n    out = {}\n    if decision != 'allowed':\n"
                       "        out.setdefault('permissionDecisionReason', 'Refused: ' + why)\n    return out\n", {4}),
        "update": ("def deny(decision, why):\n    out = {}\n    if decision != 'allowed':\n"
                   "        out.update(permissionDecisionReason='Refused: ' + why)\n    return out\n", {4}),
        "a local": ("def deny(decision, why):\n    if decision == 'allowed':\n        return {}\n"
                    "    reason = 'Refused: ' + why\n    return {'permissionDecisionReason': reason}\n", {4})}

    def test_a_hook_field_set_like_any_record_field_is_model_text(self):
        """An item assignment (plain or annotated), `+=`, `.setdefault()`
        and `.update()` set a hook field as surely as a dict entry, and a
        reason that reaches the field through a local is the parameter's
        (#4142): the hook's text and the classifier reasons are found for
        each."""
        for kind, (hook, lines) in self.HOOK_FORMS.items():
            with self.subTest(form=kind):
                spans = self._hook_spans(hook)
                self.assertEqual({a for a, _, _ in spans.get("notes/exp_4130h/hook.py", [])}, lines)
                self.assertEqual({a for a, _, _ in spans.get("notes/exp_4130h/policy.py", [])}, {3, 4, 6})

    def test_hook_output_rewritten_by_item_assignment_keeps_its_model_text(self):
        """The reviewer's equivalent rewrite of `hook_output` (#4142), which
        sets the deny reason by item assignment: its deny text is model text,
        a project name planted there and in a classifier's reason gates, and
        in every other file discovery finds the spans it finds for the dict
        form."""
        surfaces, _, texts = _discovered_with_the_round_five_rewrites()
        text = texts[NATIVE_CONTROL]
        line = text[:text.index("'Outside the CHORUS tool policy: '")].count("\n") + 1
        hits = [h for h in _scan_text(NATIVE_CONTROL, text, surfaces.files[NATIVE_CONTROL])
                if h["match"] == "CHORUS" and h["line"] == line]
        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0]["violation"] and hits[0].get("model_text_function")
                        and hits[0]["gates_in"] == ["run_controllers"], hits)
        base = _discovered()[0].files
        common = sorted((set(base) & set(surfaces.files)) - set(texts))
        self.assertEqual({rel: [tuple(s[:2]) for s in surfaces.files[rel].text_spans] for rel in common},
                         {rel: [tuple(s[:2]) for s in base[rel].text_spans] for rel in common})
        hooked = [rel for rel in common
                  if any("permissionDecisionReason" in s[2] for s in surfaces.files[rel].text_spans)]
        self.assertIn("notes/matched_cborg_2026-09-13/native_controls/native_file_policy.py", hooked)
        hits, at = self._planted("notes/matched_cborg_2026-09-13/native_controls/native_file_policy.py",
                                 "'a path outside the registered inputs and outputs'",
                                 "'a path outside the CHORUS inputs and outputs'", surfaces=surfaces)
        self.assertEqual([h["line"] for h in hits], [at])
        self.assertTrue(all(h["violation"] and h["gates_in"] == ["run_controllers"] for h in hits), hits)

    def _hook_spans(self, hook: str) -> dict:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            base = root / "notes/exp_4130h"
            _write(base / "launch.py", "from data_sheets_schema.api_runner import RunSpec\nimport hook, policy\n"
                                       "spec = RunSpec\n")
            _write(base / "hook.py", hook)
            _write(base / "policy.py", "def judge(cmd):\n"                                    # 1
                                       "    if cmd == 'x':\n"                                 # 2
                                       "        return 'allowed', 'the registered command'\n"  # 3
                                       "    return 'refused', 'not a registered command'\n"   # 4
                                       "def judge_more(cmd):\n"                               # 5
                                       "    return 'refused', 'another refusal'\n"            # 6
                                       "def unrelated():\n"                                   # 7
                                       "    return 'other', 'not a reason'\n"                 # 8
                                       "def fail():\n"                                        # 9
                                       "    raise ValueError('not a reason either')\n")       # 10
            parsed = _parsed(root, "notes")
            index = scan._notes_index(root, parsed)
            controllers, _, _ = scan.run_controllers(root, parsed, index)
            return scan.model_text_spans(root, parsed, index, controllers)

    def test_a_project_name_in_a_deny_reason_is_a_violation(self):
        """Planted in the hook's own text, in the file and command
        classifiers' reasons, and in the second line of a concatenated
        f-string reason, which is reported on its own line; a message that
        is not a reason does not gate."""
        native = "notes/matched_cborg_2026-09-13/native_controls/"
        for rel, old, new in (
                (native + "native_control.py", "'Outside the registered tool policy: '", "'Outside the CHORUS tool policy: '"),
                (native + "native_file_policy.py", "'a path outside the registered inputs and outputs'",
                 "'a path outside the CHORUS inputs and outputs'"),
                (native + "native_command_policy.py", "'a program the instruction does not prescribe'",
                 "'a CHORUS program the instruction does not prescribe'"),
                (native + "native_command_policy.py", "f'the attempt; run the registered spelling exactly: {spelling}'",
                 "f'the attempt; run the CHORUS spelling exactly: {spelling}'"),
                (native + "run_native_canary.py", "'a registered read-only lookup of this job\\'s inputs or outputs'",
                 "'a registered CHORUS lookup of this job\\'s inputs or outputs'")):
            with self.subTest(rel=rel, new=new):
                hits, line = self._planted(rel, old, new)
                # an f-string part's own line is read from Python 3.12's tokens
                if not old.startswith("f'") or sys.version_info >= (3, 12):
                    self.assertEqual([h["line"] for h in hits], [line])
                self.assertEqual(len(hits), 1, hits)
                self.assertTrue(all(h["violation"] and h.get("model_text_function") and
                                    h["gates_in"] == ["run_controllers"] for h in hits), hits)
        for rel, old, new in ((native + "native_file_policy.py", "'native file target could not be resolved'",
                               "'native CHORUS target could not be resolved'"),
                              (native + "native_control.py", "'native callback is malformed or unregistered'",
                               "'native CHORUS callback is malformed or unregistered'")):
            with self.subTest(rel=rel, new=new):
                hits, _ = self._planted(rel, old, new)
                self.assertTrue(hits and not any(h["violation"] for h in hits), hits)

    def _planted(self, rel: str, old: str, new: str, surfaces=None):
        """The CHORUS hits a copy of a real surface gains when its text `old`
        becomes `new`, under the role and text spans discovery derived (or
        `surfaces` gives), and the line `old` starts on."""
        text = (ROOT / rel).read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, (rel, old))
        surface = (surfaces or _discovered()[0]).files[rel]
        before = {(h["line"], h["context"]) for h in _scan_text(rel, text, surface) if h["match"] == "CHORUS"}
        hits = [h for h in _scan_text(rel, text.replace(old, new), surface)
                if h["match"] == "CHORUS" and (h["line"], h["context"]) not in before]
        return hits, text[:text.index(old)].count("\n") + 1


class TestTheWholeAudit(unittest.TestCase):
    """The full scan of this checkout (reads code, prompts, schema and the
    source manifest, never the record corpus)."""

    def test_the_audit_runs_and_every_approach_has_a_surface(self):
        result = _full_run()
        self.assertTrue(result["self_test"]["passed"])
        self.assertEqual(result["exit"], 1 if result["violations"] else 0)
        approaches = {a for s in result["surfaces"].values() for a in s["approaches"]}
        self.assertEqual(approaches, set(scan.APPROACHES))
        for v in result["violations"]:
            with self.subTest(path=v["path"], line=v["line"], match=v["match"]):
                self.assertEqual(v["category"], "gc_project")
                self.assertIsNone(v["exception"])
                self.assertTrue(v["gates_in"])
                self.assertTrue(all(scan.APPROACHES[a][0] for a in v["gates_in"]))
                self.assertTrue(v["model_facing"] or v["context"] in scan.CODE_CONTEXTS)
        markdown = scan.render_markdown(result)
        for live in result["facts"]["conditions"]["live"]:
            self.assertIn(f"| {live} |", markdown)
        self.assertNotIn("renderer None", markdown)
        # the report names every registered launch not shown to switch the
        # session off, and the starred element that stops the proof (#4156)
        unshown = result["facts"]["interactive"]["launches_without_customizations_off"]
        self.assertEqual(len(unshown), 4, unshown)
        for site in unshown:
            self.assertIn(f"`{site}` cannot be shown to pass `--safe-mode`", markdown)
        for spread in ("`*CLI_FLAGS`", "`*native.CLI_FLAGS`", "`*overlay['cli_flags']`", "`*runtime['cli_flags']`"):
            self.assertIn(spread, markdown)
        self.assertNotIn("does not change a registered run's verdict", markdown)
        # the derivation of the model-facing modules and its cross-check (#4085)
        self.assertIn("Cross-checked with the hand-kept `MODEL_FACING_MODULES`: derived and not listed: none; "
                      "listed and not derived (model-facing by the list alone, through a channel the flow does not "
                      "read): " + ", ".join(f"`{m}`" for m in LISTED_NOT_DERIVED) + ".", markdown)
        self.assertIn("`rereceipt`", markdown.split("A module is model-facing where the flow carries")[1][:2000])

    def test_claude_md_and_the_agent_script_demo_are_judged_as_they_run(self):
        """Root memory remains model-facing when its project examples move
        to historical reference (#5017). Any actual GC hits still gate in
        interactive sessions and unproven-safe run controllers (#4156);
        the field_prioritizer demo list in a __main__ block
        no approach runs is not a violation (#4054)."""
        result = _full_run()
        surface = _discovered()[0].files["CLAUDE.md"]
        self.assertEqual(surface.roles, dict.fromkeys(SESSION_GATES, "model_facing"))
        self.assertIn("CLAUDE.md", result["facts"]["interactive"]["memory"])
        claude = [v for v in result["violations"] if v["path"] == "CLAUDE.md"]
        # The planted-memory test independently requires a nonempty violation.
        # Removing real project examples must not require keeping one as a fixture.
        self.assertTrue(all(v["gates_in"] == SESSION_GATES for v in claude))
        demo = [h for h in result["hits"] if h["path"] == ".claude/agents/scripts/field_prioritizer.py"
                and h.get("main_block") and h["category"] == "gc_project"]
        self.assertTrue(demo)
        self.assertFalse(any(h["violation"] for h in demo))

    def test_the_review_round_three_findings_are_violations(self):
        """The GC names in d4d-review-record's description (interactive
        sessions, and run_controllers while no registered launch is shown to
        switch them off) and the renderer's study-group table all gate
        (#4091); the report says registered runs are unaffected only where
        every launch is shown to pass --safe-mode, which no launch of this
        checkout is (#4092, #4156), and names the instruction file nothing
        loads (#4093)."""
        result = _full_run()
        found = {(v["path"], v["match"].lower(), tuple(v["gates_in"])) for v in result["violations"]}
        for want in ((".claude/agents/d4d-review-record.md", "chorus", tuple(SESSION_GATES)),
                     (".claude/agents/d4d-review-record.md", "ai_readi", tuple(SESSION_GATES)),
                     ("src/data_sheets_schema/rendering/human_readable_renderer.py", "diabet", ("native_agentic",))):
            with self.subTest(want=want):
                self.assertIn(want, found)
        markdown = scan.render_markdown(result)
        self.assertIn("NOT every registered native launch is shown to pass `--safe-mode`", markdown)
        self.assertNotIn("Every registered native launch passes `--safe-mode`", markdown)
        self.assertIn("`.github/workflows/d4d_assistant_edit.md` (loaded by nothing: not a surface)", markdown)

    def test_the_skills_own_description_has_a_recorded_reason(self):
        """Every session lists this skill's description, which names the
        categories it audits: its tracked hits carry the exception that says
        so, and none is a project name (#4131)."""
        result = _full_run()
        rel = ".claude/skills/d4d-generation-specificity-audit/SKILL.md"
        listed = [h for h in result["hits"] if h["path"] == rel and h.get("loaded_in")]
        self.assertTrue(listed)
        self.assertFalse([h for h in listed if h["category"] == "gc_project"])
        self.assertTrue(all(h["exception"] is not None for h in listed), listed)
        entry = result["exceptions"][listed[0]["exception"]]
        self.assertEqual(entry["path"], rel)
        self.assertTrue(entry["reason"].strip())
        # read on a tree without the skill (origin/main before this PR), the
        # entry is unused, and the report says why rather than calling it stale
        line = scan._unused_exceptions([{**entry, "hits": 0}, {"index": 99, "path": "CLAUDE.md", "hits": 0}],
                                       ["CLAUDE.md"])
        self.assertEqual(line, f"Unused exceptions (stale, or the finding was fixed): #{entry['index']} (names no "
                               "surface of this checkout), #99")


if __name__ == "__main__":
    unittest.main()


class TestOfflineDraftSurface(unittest.TestCase):
    def test_declared_offline_prompt_is_scanned_without_live_delivery_claim(self):
        surfaces, facts = _discovered()
        rel = 'src/data_sheets_schema/source_heading_routing.py'
        surface = surfaces.files[rel]
        self.assertEqual(surface.roles['offline_draft'], 'model_facing')
        self.assertIn(rel, facts['offline_draft_surfaces'])
        # Its compiler now validates the explicit live capture. Its offline
        # instruction text is still not the live model-facing projection.
        self.assertIn(rel, facts['api_closure'])
        self.assertEqual(surface.roles['api'], 'run_shaping')
        live = 'src/data_sheets_schema/source_heading_runtime.py'
        self.assertEqual(surfaces.files[live].roles['api'], 'model_facing')
        self.assertEqual(set(facts['conditions']['registered_routing_conditions']),
            {'generic_v10_source_heading_routing_v1', 'generic_v10_source_heading_span_v1'})
        hits, _ = _plant(rel, 'POLICY_PROBE = "Always describe CM4AI."')
        self.assertTrue(any(h['violation'] and 'offline_draft' in h['gates_in'] for h in hits))
