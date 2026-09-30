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

import pytest
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


class TestTheAliasesOfAnEntry(unittest.TestCase):
    """#1070: `related_ids` iterated a scalar `also_known_as` character by
    character, so the identifier map held single characters instead of the
    alias and a record naming that alias passed the check. The renderer half
    was #1068; this is the checker's, and both read one definition now."""

    def test_a_scalar_alias_is_one_identifier_not_its_characters(self):
        entry = {"id": "https://doi.org/10.1/PROJ", "also_known_as": "https://doi.org/10.1/PROJ.v2"}
        self.assertEqual(scope.aliases_of(entry), ["https://doi.org/10.1/PROJ", "https://doi.org/10.1/PROJ.v2"])

    def test_a_list_and_no_alias_at_all(self):
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": ["b", " c "]}), ["a", "b", "c"])
        self.assertEqual(scope.aliases_of({"id": "a"}), ["a"])
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": None}), ["a"])
        self.assertEqual(scope.aliases_of("not an entry"), [])

    def test_a_numeric_alias_and_a_repeated_id(self):
        """A numeric scalar raised TypeError out of the scope block on main —
        a run-ending crash, not a wrong map (#1153 review, N4); an id repeated
        among its aliases is listed once."""
        self.assertEqual(scope.aliases_of({"id": "doi:1", "also_known_as": 12345}), ["doi:1", "12345"])
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": ["a", "b", None, ""]}), ["a", "b"])

    def test_aliases_no_reader_can_match_are_not_aliases(self):
        """#1157: a bool, bytes, a nested list or a mapping absorbed into a
        plausible-looking alias that never matches (`True`, `b'…'`, the
        mapping's keys); they are skipped, and `check_manifest` reports them."""
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": True}), ["a"])
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": b"bytes"}), ["a"])
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": {"k": "v"}}), ["a"])
        self.assertEqual(scope.aliases_of({"id": "a", "also_known_as": ["b", ["c"], {"d": 1}, False, 7]}), ["a", "b", "7"])
        self.assertEqual(scope.aliases_of({"id": True}), [])

    def test_a_malformed_entry_is_reported_by_the_manifest_check_the_checker_and_the_cli(self):
        """#1157: the two readers of the declaration name the same rows, the
        CLI lists them without raising (#1177 review, M1), and an `id` that
        is not an identifier is reported, not dropped (S1)."""
        import click.testing
        from data_sheets_schema.cli.download import scope_cmd
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "m.yaml"
            manifest.write_text(yaml.safe_dump({"projects": {"P": [], "Q": []}, "scope": {"P": {
                "referent": "P", "referent_id": "https://doi.org/10.1/P",
                "related_but_distinct": ["https://doi.org/10.1/BARE", None,
                                         {"id": "https://doi.org/10.1/OTHER", "name": "Other", "express_as": "related_datasets",
                                          "also_known_as": ["https://doi.org/10.1/OTHER.v3", {"oops": 1}, True]},
                                         {"id": True, "name": "Boolish", "express_as": "related_datasets"},
                                         {"name": "NoId", "express_as": "related_datasets"},
                                         {"id": ["doi:1"], "name": "Listy", "express_as": "related_datasets"},
                                         {"id": ["doi:10.1/REAL"], "name": "Half", "express_as": "related_datasets",
                                          "also_known_as": "https://doi.org/10.1/ALIAS", "manifest_key": ["Q"], "in_bundle": ["s1", {"x": 1}]},
                                         {"id": "https://doi.org/10.1/THIRD", "name": "Third", "express_as": "related_datasets",
                                          "also_known_as": b"raw"},
                                         {"id": ["doi:10.1/BOTH"], "name": "Both", "express_as": "related_datasets",
                                          "also_known_as": ["https://doi.org/10.1/BOTH.alias", True]}]}}}))
            rows = scope.malformed_entries("P", manifest)
            problems = [p["problem"] for p in scope.check_manifest(manifest) if p["project"] == "P"]
            ids = scope.related_ids("P", manifest)
            r = click.testing.CliRunner(mix_stderr=False).invoke(scope_cmd, ["--check", "--manifest", str(manifest)])
        self.assertEqual([(x["index"], x["skipped"]) for x in rows],
                         [(0, True), (1, True), (2, False), (3, True), (4, True), (5, True), (6, False), (7, False), (8, False), (8, False)])
        self.assertIn("`id` is a list, not an identifier; only the aliases are read", rows[6]["problem"])   # SF2
        self.assertTrue(any("manifest_key is a list" in p for p in problems), problems)                      # SF1
        self.assertTrue(any("in_bundle carries a dict" in p for p in problems), problems)
        self.assertTrue(any("claims source 's1'" in p for p in problems), problems)
        self.assertIn("not a mapping", rows[0]["problem"]); self.assertIn("NoneType", rows[1]["problem"])
        self.assertIn("2 value(s)", rows[2]["problem"]); self.assertIn("bool", rows[2]["problem"]); self.assertIn("dict", rows[2]["problem"])
        self.assertIn("`id` is a bool", rows[3]["problem"]); self.assertIn("no `id`", rows[4]["problem"]); self.assertIn("`id` is a list", rows[5]["problem"])
        self.assertIn("bytes", rows[7]["problem"])
        self.assertEqual([p for p in problems if "related_but_distinct[" in p],
                         [f"related_but_distinct[{x['index']}]: {x['problem']}" for x in rows])
        self.assertEqual(set(ids), {"https://doi.org/10.1/OTHER", "https://doi.org/10.1/OTHER.v3", "https://doi.org/10.1/ALIAS",
                                    "https://doi.org/10.1/THIRD", "https://doi.org/10.1/BOTH.alias"})
        # a referent_id that is a list is reported, not hashed (SF-B)
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "m.yaml"
            manifest.write_text(yaml.safe_dump({"projects": {"P": []}, "scope": {"P": {
                "referent_id": ["https://doi.org/10.1/P"], "related_but_distinct": [{"id": "doi:1", "express_as": "related_datasets"}]}}}))
            problems = [p["problem"] for p in scope.check_manifest(manifest)]
        self.assertTrue(any("referent_id is a list" in p for p in problems), problems)
        self.assertEqual(r.exit_code, 1, r.output + r.stderr)             # check_manifest problems fail the command, as before
        self.assertEqual(r.output.count("⚠️  P: related_but_distinct["), 10)        # every row, named, with the listing (SF3); both of entry 8's (SF-A)
        self.assertEqual(r.output.count("related_but_distinct[8]"), 2)
        self.assertEqual(r.output.count("that dataset is unchecked"), 5)            # the five skipped entries, once each
        self.assertEqual(r.stderr.count("related_but_distinct[2]"), 1)              # check_manifest's row, once
        self.assertIn("not about Other", r.output); self.assertIn("not about Third", r.output); self.assertIn("not about Half", r.output)
        self.assertNotIn("not about Boolish", r.output); self.assertNotIn("not about NoId", r.output)

    def test_the_block_and_the_checker_agree_on_which_entries_are_skipped(self):
        """The runner's block says "N declared entries are malformed … and
        omitted" and names the rest; the checker must skip exactly those N
        and read the rest (#1157; #1177 review, M2) — one classifier,
        `scope.malformed_in`, for both, including a falsy entry and an
        entry whose id is not an identifier."""
        from unittest import mock
        from data_sheets_schema.api_runner import scope_block
        declaration = {"referent": "the P dataset", "referent_id": "https://doi.org/10.1/P",
                       "related_but_distinct": ["bare", None, "",
                                                {"id": "https://doi.org/10.1/OTHER", "name": "Other", "express_as": "related_datasets",
                                                 "also_known_as": [True, "https://doi.org/10.1/OTHER.v2"]},
                                                {"id": True, "name": "Boolish"}, {"name": "NoId"}, 7]}
        with mock.patch.object(scope, "scope_of", lambda project, manifest=None: declaration):
            block = scope_block("P")
            rows = scope.malformed_entries("P")
        skipped = [r["index"] for r in rows if r["skipped"]]
        self.assertEqual(skipped, [0, 1, 2, 4, 5, 6])
        self.assertIn(f"({len(skipped)} declared entries are malformed", block)
        self.assertIn("Other — https://doi.org/10.1/OTHER, https://doi.org/10.1/OTHER.v2", block)   # the bool alias dropped, the entry kept
        self.assertNotIn("Boolish", block); self.assertNotIn("NoId", block)
        self.assertEqual([r["index"] for r in rows if not r["skipped"]], [3])

    def test_related_ids_maps_the_scalar_alias_to_its_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "m.yaml"
            manifest.write_text(yaml.safe_dump({"scope": {"P": {
                "referent_id": "https://doi.org/10.1/P",
                "related_but_distinct": [{"id": "https://doi.org/10.1/OTHER",
                                          "also_known_as": "https://doi.org/10.1/OTHER.v3",
                                          "express_as": "related_datasets"}]}}}))
            ids = scope.related_ids("P", manifest)
        self.assertIn("https://doi.org/10.1/OTHER.v3", ids)
        self.assertNotIn("h", ids)                                     # the first character of the alias
        self.assertEqual(set(ids), {"https://doi.org/10.1/OTHER", "https://doi.org/10.1/OTHER.v3"})

    def test_the_scope_block_and_the_checker_read_one_definition(self):
        """Proved by wiring, not by grepping the source (#1153 review, S1):
        a sentinel patched onto `scope.aliases_of` reaches the rendered
        block, so the block cannot carry a coercion of its own."""
        from unittest import mock
        from data_sheets_schema.api_runner import scope_block
        declaration = {"referent": "the P dataset", "referent_id": "https://doi.org/10.1/P",
                       "related_but_distinct": [{"id": "https://doi.org/10.1/OTHER", "name": "Other",
                                                 "express_as": "related_datasets"}]}
        with mock.patch.object(scope, "scope_of", lambda project, manifest=None: declaration), \
             mock.patch.object(scope, "aliases_of", lambda entry: ["SENTINEL-42"]):
            block = scope_block("P")
        self.assertIn("SENTINEL-42", block)


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

    @pytest.mark.corpus
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


class TestTheBareDoiAnIdentifierNames(unittest.TestCase):
    """#2916. `_norm` lower-cases because it compares; `bare_doi` writes, so it
    keeps the case and returns nothing for a value that is not a DOI."""

    def test_every_surface_form_gives_the_bare_doi_in_its_own_case(self):
        for form in ("https://doi.org/10.18130/V3/XNBOPG",
                     "http://dx.doi.org/10.18130/V3/XNBOPG",
                     "HTTPS://DOI.ORG/10.18130/V3/XNBOPG/",
                     "doi:10.18130/V3/XNBOPG",
                     "DOI:10.18130/V3/XNBOPG",
                     " 10.18130/V3/XNBOPG "):
            with self.subTest(form=form):
                self.assertEqual("10.18130/V3/XNBOPG", scope.bare_doi(form))

    def test_what_it_writes_satisfies_the_anchored_doi_pattern(self):
        """The #646 pattern, as the schema declares it."""
        pattern = re.compile(r"^10\.\d{4,}\/.+$")
        self.assertRegex(scope.bare_doi("https://doi.org/10.13026/k81f-qr68"), pattern)

    def test_a_value_that_is_not_a_doi_gives_none(self):
        for value in ("ark:59853/rocrate-chorus-ro-crate-package/",
                      "https://chorus4ai.org/",
                      "https://dataverse.lib.virginia.edu/dataset.xhtml"
                      "?persistentId=doi:10.18130/V3/XNBOPG",
                      "https://doi.org/",
                      "doi:not-a-doi",
                      "10.18130/has space",
                      "", None, 10.5555, ["https://doi.org/10.5555/x"]):
            with self.subTest(value=value):
                self.assertIsNone(scope.bare_doi(value))


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

    def test_an_entry_naming_the_referent_by_alias_spelling_or_key_is_caught(self):
        """#3584. The exact raw id was the only self-reference reported, so
        an alias, a `doi:`/bare/cased/slashed spelling of the referent's DOI
        or a manifest_key naming the project itself passed -- while
        `check_record` would read a record carrying its own DOI as out of
        scope. Each entry is named by its index and what it matched on; a
        control entry beside it is not."""
        own = "https://doi.org/10.1234/OWN"
        cases = [
            ({"id": own}, "id / also_known_as 'https://doi.org/10.1234/OWN'"),
            ({"id": "https://example.org/x", "also_known_as": "doi:10.1234/own"},
             "id / also_known_as 'doi:10.1234/own'"),
            ({"also_known_as": ["https://example.org/y", "10.1234/OWN/"]},
             "id / also_known_as '10.1234/OWN/'"),
            ({"id": "HTTP://DX.DOI.ORG/10.1234/own"}, "id / also_known_as 'HTTP://DX.DOI.ORG/10.1234/own'"),
            ({"id": "https://example.org/x", "manifest_key": "P"}, "manifest_key 'P'"),
        ]
        for entry, how in cases:
            with self.subTest(entry=entry):
                m = self._manifest({"P": {"referent_id": own, "related_but_distinct": [
                    {"id": "https://example.org/other"}, entry]}})
                rows = [p["problem"] for p in scope.check_manifest(m)]
                self.assertEqual(rows, [f"related_but_distinct[1] names the referent itself ({how}): "
                                        "the referent is also listed as related-but-distinct"])
        # Another dataset, and a referent that is not an identifier, name
        # nothing.
        for block in ({"P": {"referent_id": own, "related_but_distinct": [
                           {"id": "doi:10.1234/OWN.v2", "also_known_as": "10.1234/OWNER"}]}},
                      {"P": {"referent_id": [own], "related_but_distinct": [{"id": own}]}}):
            with self.subTest(block=block):
                self.assertFalse(any("names the referent itself" in p["problem"]
                                     for p in scope.check_manifest(self._manifest(block))))

    def test_the_checker_and_the_release_inventory_apply_one_self_reference_test(self):
        """Proved by wiring (#3584): a sentinel patched onto
        `scope.names_referent` decides both what `check_manifest` reports
        and what `release_inventory` lists as self-referential."""
        from unittest import mock
        from data_sheets_schema import release_inventory as ri
        m = self._manifest({"P": {"referent_id": "x", "related_but_distinct": [
            {"id": "y", "in_bundle": "src_a"}]}})
        m.write_text(yaml.safe_dump({"projects": {"P": [{"id": "src_a", "source_type": "documentation",
                                                          "processed_file": "src_a.txt"}]},
                                     "scope": yaml.safe_load(m.read_text())["scope"]}))
        sentinel = [{"field": "SENTINEL-3584", "value": "y"}]
        with mock.patch.object(scope, "names_referent", lambda entry, referent, project: sentinel):
            rows = [p["problem"] for p in scope.check_manifest(m)]
            inv = ri.inventory(m.read_bytes(), None, "P")
        self.assertEqual(rows, ["related_but_distinct[0] names the referent itself (SENTINEL-3584 'y'): "
                                "the referent is also listed as related-but-distinct"])
        self.assertEqual(inv["scope"]["self_referential_entries"],
                         [{"index": 0, "matched_on": sentinel, "in_bundle": ["src_a"]}])


    def _inventoried(self, related):
        m = self._manifest({"P": {"referent_id": "https://doi.org/10.1/p",
                                  "related_but_distinct": related}})
        m.write_text(yaml.safe_dump({"projects": {"P": [{"id": "src_a", "source_type": "documentation",
                                                          "processed_file": "src_a.txt"}]},
                                     "scope": yaml.safe_load(m.read_text())["scope"]}))
        return m

    def test_a_skipped_entry_keyed_on_the_project_is_reported_as_skipped_alone(self):
        """#3679. An entry with no id and no alias is skipped by every
        reader; its manifest_key naming the project made `check_manifest`
        also call it the referent, while `release_inventory` -- which tests
        only unskipped entries -- listed it as skipped alone. Both now say
        the same one thing about it."""
        from data_sheets_schema import release_inventory as ri
        m = self._inventoried([{"manifest_key": "P", "in_bundle": "src_a"}])
        rows = [p["problem"] for p in scope.check_manifest(m)]
        self.assertEqual(rows, ["related_but_distinct[0]: no `id` and no usable alias; skipped"])
        inv = ri.inventory(m.read_bytes(), None, "P")["scope"]
        self.assertEqual([e["index"] for e in inv["skipped_entries"]], [0])
        self.assertEqual(inv["self_referential_entries"], [])

    def test_both_readers_apply_the_self_reference_test_to_the_same_entries(self):
        """#3679, by wiring: with `names_referent` patched to match every
        entry, the checker and the inventory name the same indexes -- the
        unskipped entry, never the skipped one beside it."""
        from unittest import mock
        from data_sheets_schema import release_inventory as ri
        m = self._inventoried([{"manifest_key": "P"}, {"id": "y"}])
        sentinel = [{"field": "SENTINEL-3679", "value": "v"}]
        with mock.patch.object(scope, "names_referent", lambda entry, referent, project: sentinel):
            rows = [p["problem"] for p in scope.check_manifest(m)
                    if "names the referent itself" in p["problem"]]
            inv = ri.inventory(m.read_bytes(), None, "P")["scope"]
        self.assertEqual(rows, ["related_but_distinct[1] names the referent itself (SENTINEL-3679 'v'): "
                                "the referent is also listed as related-but-distinct"])
        self.assertEqual([e["index"] for e in inv["self_referential_entries"]], [1])


class TestOneReaderOfTheManifestBytes(unittest.TestCase):
    """#3415. `scope_in` (#3283) reads a declaration off the bytes
    `release_inventory` hashes; the path readers and `check_manifest` used
    to parse the file themselves and repeat the `in_bundle` shape handling.
    Now there is one parse and one reading of `in_bundle`."""

    def _manifest(self, text):
        tmp = tempfile.NamedTemporaryFile("wb", suffix="_3415.yaml", delete=False)
        tmp.write(text.encode("utf-8") if isinstance(text, str) else text)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_the_path_readers_and_the_byte_reader_share_one_parse(self):
        from unittest import mock
        m = self._manifest("scope: {}\n")
        parsed = {"scope": {"P": {"referent_id": "SENTINEL-3415"}}}
        with mock.patch.object(scope, "_parse", lambda encoded: parsed):
            self.assertEqual(scope.scope_of("P", m), {"referent_id": "SENTINEL-3415"})
            self.assertEqual(scope.scope_in(b"scope: {}\n", "P"), {"referent_id": "SENTINEL-3415"})

    def test_check_manifest_reads_the_file_once(self):
        """It used to re-open the file per project for the malformed-entry
        rows, so those rows and the rest could describe two files."""
        from unittest import mock
        m = self._manifest(yaml.safe_dump({"projects": {"P": [{"id": "s"}], "Q": [{"id": "t"}]}, "scope": {
            "P": {"referent_id": "x", "related_but_distinct": ["bare"]},
            "Q": {"referent_id": "y", "related_but_distinct": [None]}}}))
        real, calls = scope._parse, []
        with mock.patch.object(scope, "_parse", lambda encoded: calls.append(1) or real(encoded)):
            problems = [p["problem"] for p in scope.check_manifest(m)]
        self.assertEqual(len(calls), 1)
        self.assertEqual(problems, ["related_but_distinct[0]: entry is a str, not a mapping; skipped",
                                    "related_but_distinct[0]: entry is a NoneType, not a mapping; skipped"])

    def test_check_manifest_reads_in_bundle_through_the_shared_helper(self):
        """Structural, because the wiring is behaviour-preserving: an inline
        copy of the `in_bundle` shape handling gives the same rows as the
        helper, so no output-only test can tell them apart (#3662). Patching
        the helper to answer a sentinel shows `check_manifest` asks it."""
        from unittest import mock
        m = self._manifest(yaml.safe_dump({"projects": {"P": [{"id": "s1"}]}, "scope": {"P": {
            "referent_id": "x", "related_but_distinct": [{"id": "y", "in_bundle": ["s1"]}]}}}))
        with mock.patch.object(scope, "_in_bundle_as_written", lambda entry: ["SENTINEL-3650"]):
            problems = [p["problem"] for p in scope.check_manifest(m)]
            self.assertEqual(scope.in_bundle_of({"in_bundle": ["s1"]}), ["SENTINEL-3650"])
        self.assertEqual(problems, [
            "related dataset claims source 'SENTINEL-3650' is in this bundle; "
            "the manifest lists no such source for P"])

    def test_the_in_bundle_rows_keep_the_order_written(self):
        """A value that is not an identifier is reported in its place among
        the identifiers, and the identifiers `check_manifest` matches are
        the ones `in_bundle_of` gives. This checks output only; that the
        checker reads `in_bundle` through the shared helper is the test
        above (#3662)."""
        written = ["gone", {"k": 1}, "s1", True, 7]
        m = self._manifest(yaml.safe_dump({"projects": {"P": [{"id": "s1"}]}, "scope": {"P": {
            "referent_id": "x", "related_but_distinct": [{"id": "y", "in_bundle": written}]}}}))
        problems = [p["problem"] for p in scope.check_manifest(m)]
        self.assertEqual(problems, [
            "related dataset claims source 'gone' is in this bundle; the manifest lists no such source for P",
            "related dataset's in_bundle carries a dict, not a source id",
            "related dataset's in_bundle carries a bool, not a source id",
            "related dataset claims source 7 is in this bundle; the manifest lists no such source for P"])
        self.assertEqual(scope.in_bundle_of({"in_bundle": written}), ["gone", "s1", 7])

    def test_a_path_reader_keeps_the_parsers_own_errors(self):
        """Behaviour-preserving: the path readers raised the decoder's or
        the parser's error when they opened the file themselves, and still
        do; the byte reader says `ValueError`, as it did."""
        bad_yaml, bad_utf8 = self._manifest("scope: [unclosed\n"), self._manifest(b"scope: \xff\n")
        with self.assertRaises(yaml.YAMLError):
            scope.load_manifest(bad_yaml)
        with self.assertRaises(UnicodeDecodeError):
            scope.scope_of("P", bad_utf8)
        for raw in (bad_yaml.read_bytes(), bad_utf8.read_bytes()):
            with self.assertRaises(ValueError):
                scope.scope_in(raw, "P")
        self.assertEqual(scope.load_manifest(Path(tempfile.gettempdir()) / "absent_3415.yaml"), {})


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
