"""#422 — scope belongs in the manifest, not in the launch prompt.

The VOICE launch prompt for the 2026-08-07 sweep carried a paragraph naming the
project, the pediatric dataset, a file not to read, and the issue number of the
last time it went wrong. It worked. It was also the wrong layer, the wrong kind
of statement, and inherited by nothing: any new dataset with a companion cohort
needs someone to notice and write another one.

These tests hold the replacement in place from both ends — the declaration is
consistent and checkable, and the instruction that goes out carries no
project-specific text that could quietly become load-bearing again.
"""

import re
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import scope
from data_sheets_schema.constants import PROJECTS

ALL_PROJECTS = (*PROJECTS, "VOICE_PEDIATRIC")


class TestTheDeclarationItself(unittest.TestCase):
    def test_every_project_declares_a_scope(self):
        """A new dataset declares two lines and inherits the check. One that
        declares nothing is the state this issue is about."""
        declared = scope.all_scopes()
        for project in ALL_PROJECTS:
            with self.subTest(project=project):
                self.assertIn(project, declared)
                self.assertTrue(declared[project].get("referent_id"))

    def test_the_declaration_is_internally_consistent(self):
        """A declaration naming a project or a source that does not exist is
        worse than none: it reads as a control and enforces nothing."""
        self.assertEqual([], scope.check_manifest())

    def test_the_voice_pair_declares_each_other(self):
        self.assertIn("VOICE_PEDIATRIC",
                      [e.get("manifest_key")
                       for e in scope.scope_of("VOICE")["related_but_distinct"]])
        self.assertIn("VOICE",
                      [e.get("manifest_key") for e in
                       scope.scope_of("VOICE_PEDIATRIC")["related_but_distinct"]])

    def test_the_pediatric_source_is_declared_as_present_in_voices_bundle(self):
        """VOICE's bundle really does contain the pediatric PhysioNet record,
        because the current VOICE documentation advertises the two together.
        Dropping the source to make the rule easier to state would make the
        bundle a worse description of the evidence."""
        entry = scope.scope_of("VOICE")["related_but_distinct"][0]
        self.assertEqual("physionet_pediatric_1_1_0", entry["in_bundle"])
        self.assertEqual("related_datasets", entry["express_as"])

    def test_version_dois_are_covered_not_only_the_project_doi(self):
        """PhysioNet mints a DOI per version as well as one per project. A
        check that knew only the project-level DOI would pass a record that
        named the version — which is the form the records actually use."""
        ids = scope.related_ids("VOICE")
        self.assertIn("https://doi.org/10.13026/h995-bt35", ids)
        self.assertIn("https://doi.org/10.13026/mf9s-5r03", ids)


class TestCheckingARecord(unittest.TestCase):
    def test_a_record_about_the_companion_cohort_is_caught(self):
        status, why = scope.check_record(
            "VOICE", {"id": "https://doi.org/10.13026/h995-bt35"})
        self.assertEqual("out_of_scope", status)
        self.assertIn("related_datasets", why)

    def test_identifier_spelling_does_not_let_it_through(self):
        """`doi:10.…` and `https://doi.org/10.…` name the same dataset, and a
        check that answered "no match" for one would be an invitation to write
        that one."""
        for spelling in ("doi:10.13026/h995-bt35",
                         "https://doi.org/10.13026/h995-bt35/",
                         "HTTPS://DOI.ORG/10.13026/H995-BT35"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    "out_of_scope",
                    scope.check_record("VOICE", {"id": spelling})[0])

    def test_the_adult_dataset_is_in_scope_for_voice(self):
        for ident in ("https://doi.org/10.13026/37yb-1t42",
                      "https://doi.org/10.13026/8xbn-nq66",
                      "https://b2ai-voice.org/"):
            with self.subTest(ident=ident):
                self.assertEqual(
                    ("ok", None), scope.check_record("VOICE", {"id": ident}))

    def test_a_release_doi_is_not_failed_for_not_being_the_referent(self):
        """Records legitimately identify themselves by a release DOI, a landing
        page or an ARK. Failing that variety would be a naming rule wearing a
        scope rule's coat."""
        self.assertEqual("ok", scope.check_record(
            "AI_READI", {"id": "https://doi.org/10.60775/fairhub.2"})[0])

    def test_bare_and_dx_doi_spellings_do_not_slip_through(self):
        """#442. `uriorcurie` slots accept bare tokens (#402), so a bare DOI is
        a form records actually take — and one the check answered `ok` for."""
        for spelling in ("10.13026/h995-bt35",
                         "http://dx.doi.org/10.13026/h995-bt35",
                         "https://dx.doi.org/10.13026/h995-bt35"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    "out_of_scope",
                    scope.check_record("VOICE", {"id": spelling})[0])

    def test_an_unreadable_record_is_reported_not_raised(self):
        """#444. One unparseable file must not abort a sweep of 329."""
        bad = Path(tempfile.mkstemp(suffix=".yaml")[1])
        self.addCleanup(lambda: bad.unlink(missing_ok=True))
        bad.write_text("id: [unclosed\n")
        status, why = scope.check_record("VOICE", bad)
        self.assertEqual("unreadable", status)
        self.assertIn("Error", why)

    def test_a_project_with_no_declaration_is_reported_not_failed(self):
        status, why = scope.check_record("NOT_A_PROJECT", {"id": "x"})
        self.assertEqual("undeclared", status)
        self.assertIn("no scope declared", why)

    def test_the_whole_corpus_agrees_with_the_declaration(self):
        """329 records at the time of writing (full and core), none about the
        other cohort. The paragraph was belt-and-braces; this is the braces."""
        from data_sheets_schema.api_runner import CONCAT_DIR
        bad = []
        for rec in [*CONCAT_DIR.glob("*/*/*_d4d.yaml"),
                    *CONCAT_DIR.glob("*/*/*_d4d_core.yaml")]:
            project = (rec.name.replace("_d4d_core.yaml", "")
                       .replace("_d4d.yaml", ""))
            if project not in ALL_PROJECTS:
                continue
            try:
                data = yaml.safe_load(rec.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                continue
            if scope.check_record(project, data)[0] == "out_of_scope":
                bad.append(str(rec))
        self.assertEqual([], bad)


class TestTheOtherCohortAbsorbedOneLevelDown(unittest.TestCase):
    """#441. `check_record` settles what a record is *about* and said 329 of 329
    were fine, while 32 of them placed the pediatric release inside VOICE's own
    resources and distribution. Not a record about the wrong dataset — a record
    absorbing the other dataset into its own."""

    def test_an_identifier_in_the_declared_slot_is_not_reported(self):
        refs = scope.foreign_references("VOICE", {
            "id": "https://doi.org/10.13026/37yb-1t42",
            "related_datasets": [
                {"target_dataset": "https://doi.org/10.13026/h995-bt35"}]})
        self.assertEqual([], refs)

    def test_an_identifier_in_the_distribution_is_reported(self):
        refs = scope.foreign_references("VOICE", {
            "id": "https://doi.org/10.13026/37yb-1t42",
            "distribution_formats": [
                {"access_urls": ["https://physionet.org/content/"
                                 "b2ai-voice-pediatric/1.1.0/"]}]})
        self.assertEqual(1, len(refs))
        self.assertEqual("distribution_formats[0].access_urls[0]",
                         refs[0]["path"])

    def test_a_bare_doi_nested_deep_is_reported(self):
        refs = scope.foreign_references("VOICE", {
            "resources": [{"version_access":
                           {"latest_version_doi": "10.13026/mf9s-5r03"}}]})
        self.assertEqual(["resources[0].version_access.latest_version_doi"],
                         [r["path"] for r in refs])

    def test_a_project_with_nothing_declared_distinct_reports_nothing(self):
        self.assertEqual([], scope.foreign_references(
            "AI_READI", {"id": "x", "resources": [{"id": "y"}]}))

    def test_it_is_reported_and_never_a_verdict(self):
        """32 records carry these placements. Failing them would be the
        retroactive-failure error the live-provenance cutoff exists to avoid,
        and some placements are legitimate citations."""
        record = {"id": "https://doi.org/10.13026/37yb-1t42",
                  "resources": [{"id": "https://doi.org/10.13026/h995-bt35"}]}
        self.assertEqual(("ok", None), scope.check_record("VOICE", record))
        self.assertEqual(1, len(scope.foreign_references("VOICE", record)))


class TestAMalformedDeclarationIsCaught(unittest.TestCase):
    """`check_manifest` is the reason the declaration can be trusted; if it
    passed anything, the block would be prose again."""

    def _manifest(self, scope_block):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        yaml.safe_dump({"projects": {"P": [{"id": "src_a"}]},
                        "scope": scope_block}, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_a_scope_for_an_unknown_project(self):
        m = self._manifest({"Q": {"referent_id": "x"}})
        self.assertTrue(any("no sources for" in p["problem"]
                            for p in scope.check_manifest(m)))

    def test_a_referent_stated_only_in_prose(self):
        m = self._manifest({"P": {"referent": "a dataset"}})
        self.assertTrue(any("prose only" in p["problem"]
                            for p in scope.check_manifest(m)))

    def test_a_related_dataset_naming_a_project_that_does_not_exist(self):
        m = self._manifest({"P": {"referent_id": "x", "related_but_distinct":
                                  [{"id": "y", "manifest_key": "NOPE"}]}})
        self.assertTrue(any("does not exist" in p["problem"]
                            for p in scope.check_manifest(m)))

    def test_a_related_dataset_claiming_a_source_the_bundle_lacks(self):
        m = self._manifest({"P": {"referent_id": "x", "related_but_distinct":
                                  [{"id": "y", "in_bundle": "src_missing"}]}})
        self.assertTrue(any("no such source" in p["problem"]
                            for p in scope.check_manifest(m)))

    def test_a_one_directional_declaration_is_caught(self):
        """#443. A declaration in one direction checks in one direction: a
        pediatric record identifying itself by the adult DOI would pass."""
        m = self._manifest({
            "P": {"referent_id": "x", "related_but_distinct":
                  [{"id": "y", "manifest_key": "Q"}]},
            "Q": {"referent_id": "y", "related_but_distinct": []},
        })
        # Q must exist in `projects` for the first check to stay quiet.
        data = yaml.safe_load(m.read_text())
        data["projects"]["Q"] = [{"id": "src_b"}]
        m.write_text(yaml.safe_dump(data))
        self.assertTrue(any("one direction only" in p["problem"]
                            for p in scope.check_manifest(m)))

    def test_a_related_dataset_outside_the_corpus_needs_no_back_reference(self):
        """An upstream cohort or partner registry legitimately has no scope
        block here, and requiring one would force fictional entries."""
        m = self._manifest({"P": {"referent_id": "x", "related_but_distinct":
                                  [{"id": "y", "manifest_key": None}]}})
        self.assertEqual([], scope.check_manifest(m))

    def test_a_referent_that_is_also_declared_distinct_from_itself(self):
        m = self._manifest({"P": {"referent_id": "x", "related_but_distinct":
                                  [{"id": "x"}]}})
        self.assertTrue(any("also listed as" in p["problem"]
                            for p in scope.check_manifest(m)))


class TestTheInstructionCarriesNoProjectSpecificScope(unittest.TestCase):
    """The mirror of the existing test that the prompt *file* names no project
    (`test_generic_v2_prompt.py`), moved to the artifact that is actually sent.

    A file can be generic and the instruction still not be: substitution
    happens in between, and on the agentic path a human used to compose the
    launch text by hand.
    """

    def _rendered(self, project, condition):
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        return resolve_prompt(RunSpec(
            project=project, arm="BASELINE", method="claudecode_agent",
            bundle=Path(f"data/preprocessed/concatenated/{project}"
                        f"_preprocessed.txt"),
            label="L", condition=condition, manifest_line="",
            run_date="2026-08-11"))

    def test_no_rendered_instruction_names_another_project(self):
        from data_sheets_schema.api_runner import CONDITION_PROMPTS
        for condition in sorted(CONDITION_PROMPTS):
            for project in ALL_PROJECTS:
                text = self._rendered(project, condition)
                for other in ALL_PROJECTS:
                    if other == project:
                        continue
                    with self.subTest(condition=condition, project=project,
                                      other=other):
                        # Word-bounded: `VOICE` is a prefix of
                        # `VOICE_PEDIATRIC`, so a substring test would report
                        # the pediatric name as the adult one and pass the
                        # exact case this exists to catch.
                        self.assertIsNone(
                            re.search(rf"\b{other}\b", text),
                            f"the {condition} instruction for {project} names "
                            f"{other}")

    def test_a_rendered_instruction_names_only_its_own_bundle(self):
        """The paragraph's operative sentence was *"Do not read
        `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`"* — a
        second bundle named in an instruction that declares one.

        Banning directive phrases outright would be wrong: the prompt's uniform
        rules are directives (`OUTPUTS — do not write outside these three`) and
        they apply to every project identically. What must not appear is
        another dataset's bundle.
        """
        from data_sheets_schema.api_runner import CONDITION_PROMPTS
        pattern = re.compile(r"data/preprocessed/concatenated/[\w.-]+")
        for condition in sorted(CONDITION_PROMPTS):
            for project in ALL_PROJECTS:
                text = self._rendered(project, condition)
                named = set(pattern.findall(text))
                expected = {f"data/preprocessed/concatenated/{project}"
                            f"_preprocessed.txt"}
                with self.subTest(condition=condition, project=project):
                    self.assertEqual(expected, named)


class TestThePlaybooksCarryNoPerProjectScope(unittest.TestCase):
    """`.claude/` is the launch template on the agentic path — the one place a
    per-GC paragraph could live and still be invisible to the prompt-condition
    tests, which inspect the prompt file."""

    DIRECTIVES = ("do not read", "must not read", "never read", "out of scope",
                  "separate project", "scope boundary", "only covers")

    def test_no_playbook_line_scopes_a_named_project(self):
        offenders = []
        for path in sorted(Path(".claude").rglob("*.md")):
            for n, line in enumerate(path.read_text(encoding="utf-8")
                                     .splitlines(), 1):
                named = any(re.search(rf"\b{p}\b", line) for p in ALL_PROJECTS)
                directs = any(d in line.lower() for d in self.DIRECTIVES)
                if named and directs:
                    offenders.append(f"{path}:{n}: {line.strip()[:110]}")
        self.assertEqual([], offenders,
                         "a per-project scope directive belongs in the "
                         "manifest's `scope:` block, not in a playbook")

    def test_the_playbook_says_where_scope_goes(self):
        text = Path(".claude/commands/d4d-full-core.md").read_text(
            encoding="utf-8")
        self.assertIn("scope", text.lower())
        self.assertIn("source_manifest.yaml", text)


if __name__ == "__main__":
    unittest.main()
