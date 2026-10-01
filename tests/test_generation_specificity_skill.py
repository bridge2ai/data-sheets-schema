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
- discovery finds every model client, controller and named playbook or
  agent from the code rather than a glob list (#4023);
- the "api" section's derivations agree with what the runtime does, and fail
  loudly rather than fall back (#4022, #4025);
- a broken configuration or an unexpected error is exit 2, never 1 (#4027).

None of these tests walks the record corpus (`data/d4d_concatenated`), so
none is marked `corpus` (#4027).
"""
from __future__ import annotations

import ast
import importlib.util
import io
import re
import shutil
import sys
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "d4d-generation-specificity-audit"


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
        under the UVA Dataverse prefix 10.18130 (#4027)."""
        tokens = list(_tokens())
        for text in ("Use doi:10.18130/V3/HIGT4C as id", "see https://doi.org/10.18130/V3/XNBOPG",
                     "the K7TGEM release", "the F3TD5R release"):
            with self.subTest(text=text):
                self.assertIn("gc_project", {t.category for _, _, t, _ in scan.match_text(text, tokens)})


class TestTheExitStatus(unittest.TestCase):
    """Exit 1 means violations; a scan that did not happen is 2 (#4027)."""

    def _main(self, *argv):
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr"), mock.patch("sys.stdout"):
            return scan.main(["--root", str(ROOT), "--report", str(Path(d) / "r.md"), *argv])

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

    def _planted(self, rel: str, line: str):
        """Plant a line in a copy of a real surface and scan it under the
        role discover() gives that surface (#4026): a misclassified real
        surface fails these tests."""
        surface = _discovered()[0].files[rel]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / rel).parent.mkdir(parents=True)
            shutil.copy(ROOT / rel, root / rel)
            text = (root / rel).read_text(encoding="utf-8")
            if not text.endswith("\n"):
                text += "\n"
            (root / rel).write_text(text + line + "\n", encoding="utf-8")
            first = len(text.splitlines()) + 1
            hits = scan.scan_file(root, surface, list(_tokens()))
        for h in hits:
            h["exception"] = None
            h["violation"] = scan.is_violation(h)
        return [h for h in hits if h["line"] >= first], hits

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

    def test_text_above_the_prompt_body_is_header_not_model_facing(self):
        units = list(scan._markdown_units("# v9\nCHORUS rep2 changelog\n## Prompt body\nRead it.\n",
                                          prompt_header=True))
        self.assertEqual([u[1] for u in units][:3], ["header", "header", "header"])
        self.assertNotIn("header", [u[1] for u in units][3:])


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
    """Surfaces are derived from the code, not a glob list (#4023)."""

    @classmethod
    def setUpClass(cls):
        cls.surfaces, cls.facts = _discovered()

    def test_every_module_that_calls_a_model_client_is_a_surface(self):
        """Cross-checked with a text search, a different mechanism from the
        scanner's ast reading."""
        client = re.compile(r"^\s*(?:import (?:anthropic|openai)|from (?:anthropic|openai|pydantic_ai|aurelian)"
                            r"[\w.]* import)|\.messages\.create\(|\.ChatCompletion\.create\(", re.M)
        found = []
        for top in ("src", "notes"):
            for p in sorted((ROOT / top).rglob("*.py")):
                rel = p.relative_to(ROOT).as_posix()
                if scan._is_test(rel) or scan.REGISTERED_COPY.search(rel):
                    continue
                if client.search(p.read_text(encoding="utf-8", errors="ignore")):
                    found.append(rel)
        self.assertIn("src/schema_extract/process_d4d_claude_API_temp0.py", found)
        self.assertEqual([r for r in found if r not in self.surfaces.files], [])

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

    def test_every_model_facing_module_is_in_a_discovered_closure(self):
        stems = {Path(p).stem for p in self.facts["api_closure"] + self.facts["native_closure"]}
        stems |= {"healthsheet", "rocrate_normalize"}
        self.assertEqual(scan.MODEL_FACING_MODULES - stems, set())


class TestApiMeaning(unittest.TestCase):
    """The "api" section agrees with what the runtime does (#4022, #4025)."""

    @classmethod
    def setUpClass(cls):
        cls.meaning = _meaning()
        cls.cond = _discovered()[1]["conditions"]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.bundle = _write(Path(cls.tmp.name) / "X_preprocessed.txt", "hello\n")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _cli_spec(self, **kw):
        from data_sheets_schema.cli import api as cli_api
        return cli_api._spec("SOMEDATASET", "baseline", "2026-09-30_probe", None, bundle=str(self.bundle),
                             manifest=None, **kw)

    def test_the_cli_default_condition_is_what_the_cli_runs(self):
        spec = self._cli_spec()
        self.assertEqual(spec.condition, self.cond["default"])
        self.assertIn(self.cond["default"], self.cond["live"])
        self.assertIn(spec.condition, self.meaning["github_assistant"]["condition"])

    def test_the_default_renderers_are_what_the_runtime_uses(self):
        self.assertEqual(self._cli_spec().render_version, self.meaning["default_renderer"]["api"])
        agentic = sorted(self.cond["agentic_runtimes"])[0]
        self.assertEqual(self._cli_spec(runtime=agentic).render_version,
                         self.meaning["default_renderer"]["agentic"])

    def test_the_audit_floor_is_where_build_phase_refuses_the_audit(self):
        from data_sheets_schema import api_runner
        floor = self.meaning["agentic_audit_from_renderer"]
        base = self._cli_spec()
        refused = {}
        for n in (floor - 1, floor):
            spec = api_runner.RunSpec(project=base.project, arm=base.arm, method=base.method, bundle=base.bundle,
                                      label=base.label, condition=self.cond["current"], manifest=None,
                                      render_version=n)
            try:
                api_runner.build_phase(spec, "audit", carry={})
                refused[n] = False
            except Exception as exc:                # noqa: BLE001 — any other failure is not the refusal
                refused[n] = "batch-context" in str(exc)
        self.assertEqual(refused, {floor - 1: False, floor: True})

    def test_the_shape_follows_the_runner_phase_tables(self):
        from data_sheets_schema import api_runner
        model_phases = [p for p in api_runner.PHASES
                        if not (api_runner.CORE_DERIVED and p in api_runner.DERIVED_PHASES)]
        self.assertEqual(self.meaning["model_phases"], model_phases)
        expected = "MULTI-PHASE" if len(model_phases) > 1 or self.meaning["followup_turns"] else "MONOLITHIC"
        for name, row in self.meaning["conditions"].items():
            with self.subTest(condition=name):
                self.assertEqual(row["shape"], expected)
                self.assertEqual(row["model_calls_minimum"], len(model_phases))
        self.assertEqual(set(self.meaning["conditions"]), set(api_runner.CONDITION_PROMPTS))

    def test_no_api_condition_is_a_runtime_hybrid(self):
        """Renderer >= 20 is reached only by native audit continuations whose
        package refuses a parent that is not agentic generic_v9 at renderer 14
        (audit_controls/contract.py), so no API condition is a hybrid at
        runtime (#4022); the prompt-level hybrid (#4014) is kept apart."""
        ac = self.meaning["audit_continuations"]
        self.assertFalse(ac["runtime_hybrid_possible"])
        self.assertEqual(ac["uncovered"], [])
        self.assertTrue(ac["setters"])
        self.assertIn(("notes/matched_cborg_2026-09-13/audit_controls/contract.py", "generic_v9", 14),
                      {(g["path"], g["condition"], g["parent_renderer"]) for g in ac["gates"]})
        self.assertFalse(ac["api_reaches_floor"])
        for name, row in self.meaning["conditions"].items():
            with self.subTest(condition=name):
                self.assertFalse(row["runtime_hybrid"])
        self.assertTrue(any(v.startswith("No API condition is a runtime hybrid") for v in self.meaning["verdict"]))
        self.assertTrue(self.meaning["conditions"][self.cond["current"]]["prompt_hybrid"])

    def test_an_ungated_continuation_makes_a_runtime_hybrid_possible(self):
        runner = ast.parse((ROOT / scan.RUNNER).read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(ROOT / "src/data_sheets_schema/cli", root / "src/data_sheets_schema/cli")
            ctl = _write(root / "notes/x/cont/prepare.py", "manifest.update(render_version=21)\n")
            got = scan.audit_continuations(root, 20, ["notes/x/cont/prepare.py"], runner)
            self.assertTrue(got["runtime_hybrid_possible"])
            self.assertEqual(got["uncovered"], ["notes/x/cont/prepare.py:1"])
            _write(ctl.parent / "contract.py", "def check(spec):\n    if spec.condition != 'generic_v9' or "
                                               "not spec.is_agentic:\n        raise ValueError('parent')\n")
            got = scan.audit_continuations(root, 20, ["notes/x/cont/prepare.py", "notes/x/cont/contract.py"],
                                           runner)
            self.assertFalse(got["runtime_hybrid_possible"])
            # an API path that selects the floor stops at audit: reported, not a hybrid
            _write(root / scan.CLI_API, (ROOT / scan.CLI_API).read_text(encoding="utf-8")
                   + '\n@click.option("--render-version", type=int)\ndef _x(): pass\n')
            got = scan.audit_continuations(root, 20, ["notes/x/cont/prepare.py", "notes/x/cont/contract.py"],
                                           runner)
            self.assertTrue(got["api_reaches_floor"])
            self.assertFalse(got["runtime_hybrid_possible"])


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


class TestTheWholeAudit(unittest.TestCase):
    """The full scan of this checkout (~25 s; reads code, prompts, schema and
    the source manifest, never the record corpus)."""

    def test_the_audit_runs_and_every_approach_has_a_surface(self):
        result = _full_run()
        self.assertTrue(result["self_test"]["passed"])
        self.assertIn(result["exit"], (0, 1))
        approaches = {a for s in result["surfaces"].values() for a in s["approaches"]}
        self.assertEqual(approaches, set(scan.APPROACHES))
        for v in result["violations"]:
            with self.subTest(path=v["path"], line=v["line"], match=v["match"]):
                self.assertEqual(v["category"], "gc_project")
                self.assertIsNone(v["exception"])
                self.assertTrue(any(scan.APPROACHES[a][0] for a in v["approaches"]))
                self.assertTrue(v["model_facing"] or v["context"] in scan.CODE_CONTEXTS)
        markdown = scan.render_markdown(result)
        for live in result["facts"]["conditions"]["live"]:
            self.assertIn(f"| {live} |", markdown)
        self.assertNotIn("renderer None", markdown)


if __name__ == "__main__":
    unittest.main()
