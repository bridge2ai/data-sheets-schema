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
        self.assertEqual(self.facts["deterministic_sys_path"], [".claude/agents/scripts"])
        closure = set(self.facts["deterministic_closure"])
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
        missing = {name for name in scan.MODEL_FACING_MODULES
                   if f"src/data_sheets_schema/{name}.py" not in closures
                   and f"src/data_sheets_schema/{name}/__init__.py" not in closures}
        self.assertEqual(missing, set())


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
        from data_sheets_schema.shared_generation import API_POLICY
        _write(root / API_POLICY, (ROOT / API_POLICY).read_text())
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
            ('src/data_sheets_schema/api_playbook.py', 'return captured_assets()[API_POLICY]', 'return foreign()[API_POLICY]'),
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
        self.assertEqual(ex["refused"], [19, 20, 21, 22, 23, 24])
        for n in ex["refused"]:
            with self.subTest(renderer=n), self.assertRaisesRegex(ValueError, "separately registered"):
                api_runner.execute(self._spec_at(n))
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
        self.assertEqual((selection["default"], selection["enabled_values"], selection["renderers"]), (0, [1, 2], [8, 25]))
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
        self.assertEqual(selected['selection']['renderers'], [25])
        self.assertEqual(selected['selection']['conditions'], ['generic_v10'])
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
        self.assertEqual(code, 2)
        self.assertIn("notes/bad_4092.py", err.getvalue())
        self.assertIn("cannot be parsed", err.getvalue())

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

    def test_claude_md_and_the_agent_script_demo_are_judged_as_they_run(self):
        """CLAUDE.md's GC names are interactive-session violations, and
        run_controllers ones while no registered launch is shown to switch
        it off (#4156); the field_prioritizer demo list in a __main__ block
        no approach runs is not a violation (#4054)."""
        result = _full_run()
        claude = [v for v in result["violations"] if v["path"] == "CLAUDE.md"]
        self.assertTrue(claude)
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
