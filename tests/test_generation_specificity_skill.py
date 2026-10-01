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

    def test_a_non_ascii_prefix_does_not_shift_a_literal(self):
        """`ast` columns are UTF-8 bytes and `tokenize` columns are
        characters: a literal after a non-ASCII one on the same line must
        still be read from its own tokens."""
        units = list(scan._python_units("x = ('é' 'ü'); y = ('see '\n     'CHORUS here')\n"))
        self.assertIn((2, "string_literal", "CHORUS here"), [(u[0], u[1], u[2]) for u in units])

    def _planted(self, rel: str, line: str, after: str | None = None):
        """Plant a line in a copy of a real surface and scan it under the
        role discover() gives that surface (#4026): a misclassified real
        surface fails these tests. With `after`, the line goes right after
        the first line that starts with it (inside a constant or a function
        whose span discovery derived); otherwise at the end."""
        surface = _discovered()[0].files[rel]
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
        violation of that approach, and of no other."""
        surface = _discovered()[0].files["CLAUDE.md"]
        self.assertEqual(surface.roles, {"interactive_session": "model_facing"})
        planted, _ = self._planted("CLAUDE.md", "Always describe the dataset as AI-READI from FAIRhub.")
        self.assertTrue(planted)
        self.assertTrue(all(h["violation"] and h["gates_in"] == ["interactive_session"] for h in planted))

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
        and validate_d4d_completeness.py (#4054)."""
        for rel in ("src/github/generate_d4d_metadata.py", "src/github/validate_d4d_completeness.py"):
            with self.subTest(rel=rel):
                surface = self.surfaces.files[rel]
                self.assertEqual(surface.roles.get("github_assistant"), "run_shaping")
                self.assertIn("github_assistant", surface.runs)
                self.assertIn(".github/workflows/d4d_assistant_create.md", self.facts["named_files"][rel]["by"])

    def test_claude_md_is_interactive_and_registered_runs_switch_it_off(self):
        """CLAUDE.md is the project memory an interactive session loads; the
        registered native launchers pass --safe-mode, which disables it
        (#4054). The assistant instructions name it but do not hand it
        over."""
        it = self.facts["interactive"]
        self.assertIn("CLAUDE.md", it["memory"])
        self.assertIn(".github/workflows/d4d_assistant_create.md", it["memory_named_by"])
        self.assertNotIn("CLAUDE.md", self.facts["named_files"])
        for site in ("notes/matched_cborg_2026-09-13/native_controls/prepare_overlay.py",
                     "notes/claudecode_direct/prepare_direct.py",
                     "notes/matched_cborg_2026-09-13/audit_controls/native.py"):
            with self.subTest(site=site):
                self.assertTrue(any(x.startswith(site + ":") and x.endswith("--safe-mode")
                                    for x in it["customizations_off"]), it["customizations_off"])
        self.assertTrue(set(it["hooks"]) <= set(self.surfaces.files))

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
        agent runs is exposed, a script the RO-Crate arm imports is
        deterministic, and one nothing reaches is no surface. The
        field_prioritizer demo list sits in a __main__ block the arm never
        runs."""
        files = self.surfaces.files
        for rel in sorted(files):
            if rel.startswith(".claude/agents/scripts/"):
                with self.subTest(rel=rel):
                    self.assertIn(files[rel].roles.get("native_agentic"), (None, "exposed"))
        self.assertEqual(files[".claude/agents/scripts/schema_stats.py"].roles, {"native_agentic": "exposed"})
        prioritizer = files[".claude/agents/scripts/field_prioritizer.py"]
        self.assertEqual(prioritizer.roles, {"deterministic": "run_shaping"})
        self.assertEqual(prioritizer.runs, set())
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
                                  label=base.label, condition=self.cond["current"], manifest=None,
                                  render_version=renderer)

    def test_the_cli_default_condition_is_what_the_cli_runs(self):
        """The GitHub assistant's condition is the one its `d4d api run`
        names, or the CLI default when it names none, in full (#4057)."""
        spec = self._cli_spec()
        self.assertEqual(spec.condition, self.cond["default"])
        self.assertIn(self.cond["default"], self.cond["live"])
        gh = self.meaning["github_assistant"]
        workflow = (ROOT / ".github/workflows/d4d-agent.yml").read_text(encoding="utf-8")
        block = re.search(r"d4d api run(?:[^\n]*\\\n)*[^\n]*", workflow).group(0)
        named = re.search(r"--condition[\s=]+['\"]?([\w.-]+)", block)
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
        self.assertEqual(ex["refused"], [19, 20, 21, 22, 23])
        for n in ex["refused"]:
            with self.subTest(renderer=n), self.assertRaisesRegex(ValueError, "separately registered"):
                api_runner.execute(self._spec_at(n))
        allowed = max(r for r in self.meaning["audit_continuations"]["admitted_renderers"]
                      if r not in ex["refused"])
        with mock.patch.object(api_runner, "_exclusive_run", side_effect=RuntimeError("past the refusal")), \
                self.assertRaisesRegex(RuntimeError, "past the refusal"):
            api_runner.execute(self._spec_at(allowed))

    def test_the_shape_follows_the_runner_phase_tables(self):
        from data_sheets_schema import api_runner
        model_phases = [p for p in api_runner.PHASES
                        if not (api_runner.CORE_DERIVED and p in api_runner.DERIVED_PHASES)]
        self.assertEqual(self.meaning["model_phases"], model_phases)
        self.assertGreater(len(model_phases), 1)
        for name, row in self.meaning["conditions"].items():
            with self.subTest(condition=name):
                self.assertEqual(row["shape"], "MULTI-PHASE")
                self.assertEqual(row["model_calls_minimum"], len(model_phases))
        self.assertEqual(set(self.meaning["conditions"]), set(api_runner.CONDITION_PROMPTS))

    def test_the_follow_up_turns_follow_the_runner(self):
        """Re-addressing runs only under the receipt conditions, so `generic`
        (what the GitHub assistant runs) can never make it; build_readdress
        builds the full_readdress turn, not a second one (#4058)."""
        from data_sheets_schema import api_runner
        turns = self.meaning["followup_turns"]
        self.assertEqual(set(turns), {"full_readdress", "report_regate", "repair_{artifact}", "report_after_repair"})
        self.assertEqual(turns["full_readdress"]["conditions"], sorted(api_runner.RECEIPT_CONDITIONS))
        for name in ("report_regate", "repair_{artifact}", "report_after_repair"):
            self.assertIsNone(turns[name]["conditions"])
        self.assertNotIn("full_readdress", self.meaning["conditions"]["generic"]["followup_turns"])
        self.assertIn("full_readdress", self.meaning["conditions"][self.cond["current"]]["followup_turns"])
        verdict = self.meaning["verdict"][0]
        self.assertIn("full_readdress runs only under", verdict)
        self.assertNotIn("readdress, ", verdict.replace("full_readdress", ""))

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
        at renderer 14; renderer >= 20 is otherwise set only by the direct
        arm, whose runtime is agentic (#4022, #4055)."""
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
        self.assertFalse(ac["api_reaches_floor"])
        for name, row in self.meaning["conditions"].items():
            with self.subTest(condition=name):
                self.assertFalse(row["runtime_hybrid"])
        line = next(v for v in self.meaning["verdict"] if v.startswith("No API condition is a runtime hybrid"))
        self.assertIn("prepare_direct.py", line)
        self.assertNotIn("set only by native audit continuations", line)
        self.assertTrue(self.meaning["conditions"][self.cond["current"]]["prompt_hybrid"])

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
        scan.derive_followups(tree, phases, consts)
        call = '_call_with_usage(spec, "full_readdress", 1, started,'
        self.assertIn(call, self.runner_text)
        unread = ast.parse(self.runner_text.replace(call, "_call_with_usage(spec, pick_phase(), 1, started,"))
        with self.assertRaisesRegex(scan.ConfigError, "not derived: the follow-up turns"):
            scan.derive_followups(unread, phases, consts)
        no_plan = ast.parse(self.runner_text.replace('"conditional_calls":', '"other_calls":'))
        with self.assertRaisesRegex(scan.ConfigError, "conditional_calls"):
            scan.derive_followups(no_plan, phases, consts)

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
        # the report names where the registered launchers switch CLAUDE.md off
        self.assertRegex(markdown, r"native_controls/prepare_overlay\.py:\d+ --safe-mode")
        self.assertRegex(markdown, r"claudecode_direct/prepare_direct\.py:\d+ --safe-mode")

    def test_claude_md_and_the_agent_script_demo_are_judged_as_they_run(self):
        """CLAUDE.md's GC names are interactive-session violations; the
        field_prioritizer demo list in a __main__ block no approach runs is
        not a violation (#4054)."""
        result = _full_run()
        claude = [v for v in result["violations"] if v["path"] == "CLAUDE.md"]
        self.assertTrue(claude)
        self.assertTrue(all(v["gates_in"] == ["interactive_session"] for v in claude))
        demo = [h for h in result["hits"] if h["path"] == ".claude/agents/scripts/field_prioritizer.py"
                and h.get("main_block") and h["category"] == "gc_project"]
        self.assertTrue(demo)
        self.assertFalse(any(h["violation"] for h in demo))


if __name__ == "__main__":
    unittest.main()
