"""A schema-dependent recompute reads the merged schema the run recorded (#3931).

`removals.run_enum_aliases` was the one recompute that read the schema a run
recorded (#3702). The form block's undeclared-prefix count and the grounding
block's identifier walk and resolver-URL findings read today's schema and
said nothing about it. #3788 is the case that matters: the 2026-08-13 v4 rep1
VOICE run read a schema declaring `ROR`, `ORCID` and `doi`, and its commit's
blob declares none of the three. These pin the one resolution
(`run_schema.run_schema_bytes`), the rules read from its bytes, the two
blocks that now read them, and the view the rules are read from, which is
released once they are (#4082).
"""
import gzip
import hashlib
import tempfile
import unittest
import weakref
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import yaml

from data_sheets_schema import run_schema as rs
from data_sheets_schema.provenance import GitUnavailable

#: A small merged schema: it declares `foo` and no `doi`, ranges `id` and
#: `publisher` on `uriorcurie` (today's schema does too) and `lead` on Person.
RUN_SCHEMA = {
    "id": "https://example.org/run-schema", "name": "run-schema", "default_range": "string",
    "prefixes": {"foo": {"prefix_prefix": "foo", "prefix_reference": "https://foo.example.org/"},
                 "linkml": {"prefix_prefix": "linkml", "prefix_reference": "https://w3id.org/linkml/"}},
    "types": {"string": {"uri": "xsd:string", "base": "str"},
              "uriorcurie": {"uri": "xsd:anyURI", "base": "URIorCURIE"}},
    "classes": {
        "Dataset": {"attributes": {"id": {"range": "uriorcurie", "identifier": True},
                                   "publisher": {"range": "uriorcurie"},
                                   "lead": {"range": "Person"}}},
        "Person": {"attributes": {"id": {"range": "uriorcurie", "identifier": True}, "name": {}}},
    },
}

#: RUN_SCHEMA plus `VariableMetadata.unit` ranged on `uriorcurie`, as the
#: merged schema 162 of the 283 corpus records name ranged it (six versions,
#: md5 633a2d2c the most read). Today's ranges `unit` on `string` (#456), so
#: only the run's identifier slots walk it (#4081).
UNIT_SCHEMA = {**RUN_SCHEMA, "classes": {
    **RUN_SCHEMA["classes"],
    "Dataset": {"attributes": {**RUN_SCHEMA["classes"]["Dataset"]["attributes"],
                               "variables": {"range": "VariableMetadata", "multivalued": True}}},
    "VariableMetadata": {"attributes": {"name": {}, "unit": {"range": "uriorcurie"}}},
}}

GIT = "data_sheets_schema.provenance.committed_bytes_for"
REBUILT = "data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for"


def _schema_file(tmp: str, schema: dict = RUN_SCHEMA) -> tuple[Path, str, str]:
    path = Path(tmp) / "schema_all.yaml"
    path.write_text(yaml.safe_dump(schema), encoding="utf-8")
    data = path.read_bytes()
    return path, hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()


class Resolution(unittest.TestCase):
    """`run_schema_bytes`: disk, reconstruction, git, else a stated fallback."""

    def test_a_record_naming_no_schema_by_path_and_hash_reads_today(self):
        for record in (None, {}, {"schema": "x"}, {"schema": {"full_path": "x.yaml"}},
                       {"schema": {"full_sha256": "a" * 64}}, {"schema": {"full_path": "", "full_md5": "m"}}):
            self.assertEqual(rs.run_schema_bytes(record),
                             (None, {"source": rs.TODAY,
                                     "reason": "the record names no merged schema by path and hash"}))

    def test_the_file_on_disk_is_read_where_every_recorded_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, sha, md5 = _schema_file(tmp)
            for given in ({"full_sha256": sha}, {"full_md5": md5}, {"full_sha256": sha, "full_md5": md5}):
                data, basis = rs.run_schema_bytes({"schema": {"full_path": str(path), **given}})
                self.assertEqual(data, path.read_bytes())
                self.assertEqual(basis["source"], "the run's schema, on disk")
            # One recorded hash that does not match is not the run's file: git is asked.
            with mock.patch(REBUILT, return_value=None), mock.patch(GIT, return_value=None) as git:
                data, basis = rs.run_schema_bytes({"schema": {"full_path": str(path), "full_sha256": sha,
                                                              "full_md5": "0" * 32}})
            git.assert_called_once_with(str(path), md5="0" * 32, sha256=sha)
            self.assertIsNone(data)
            self.assertIn("no committed version", basis["reason"])

    def test_a_reconstruction_is_read_before_git_is_asked(self):
        """#3953: a shallow clone cannot answer git, so the committed artefact comes first."""
        record = {"schema": {"full_path": "src/x_all.yaml", "full_sha256": "a" * 64}}
        entry = {"artefact": "notes/x.yaml.gz", "base_commit": "b" * 40, "matched_on": ["sha256"],
                 "observed_at": "a branch commit", "issue": 3788}
        with mock.patch(REBUILT, return_value=(b"bytes", entry)) as rebuilt, \
                mock.patch(GIT, side_effect=AssertionError("git must not be asked")):
            data, basis = rs.run_schema_bytes(record)
        rebuilt.assert_called_once_with("src/x_all.yaml", md5=None, sha256="a" * 64)
        self.assertEqual(data, b"bytes")
        self.assertEqual(basis, {"source": "the run's schema, reconstructed", "path": "src/x_all.yaml",
                                 "sha256": "a" * 64, "artefact": "notes/x.yaml.gz", "base_commit": "b" * 40,
                                 "matched_on": ["sha256"], "observed_at": "a branch commit",
                                 "reconstruction": "reconstructed_bytes.RECONSTRUCTIONS (#3788)"})

    def test_a_committed_version_is_read_with_its_commit(self):
        record = {"schema": {"full_path": "src/x_all.yaml", "full_md5": "m" * 32}}
        with mock.patch(REBUILT, return_value=None), \
                mock.patch(GIT, return_value=(b"bytes", {"commit": "c" * 40, "matched_on": ["md5"]})) as git:
            data, basis = rs.run_schema_bytes(record)
        git.assert_called_once_with("src/x_all.yaml", md5="m" * 32, sha256=None)
        self.assertEqual(data, b"bytes")
        self.assertEqual(basis, {"source": "the run's schema, a git blob", "path": "src/x_all.yaml",
                                 "md5": "m" * 32, "commit": "c" * 40, "matched_on": ["md5"]})

    def test_every_failure_is_the_stated_fallback_never_a_traceback(self):
        """A shallow clone, git that cannot be started (#3851), git refusing
        to run, no matching version, an unreadable reconstruction: each is
        today's schema with its reason, the recorded hash kept."""
        record = {"schema": {"full_path": "src/x_all.yaml", "full_sha256": "a" * 64}}
        cases = (
            (None, GitUnavailable("shallow clone"), "git cannot answer (shallow clone)"),
            (None, FileNotFoundError(2, "No such file or directory", "git"),
             "git could not be run (FileNotFoundError"),
            (None, PermissionError(13, "Permission denied", "git"), "git could not be run (PermissionError"),
            (None, None, "no committed version of the path hashes to what the record recorded"),
            (PermissionError(13, "Permission denied", "x.yaml.gz"), AssertionError("not reached"),
             "its recorded reconstruction could not be read (PermissionError"),
        )
        for rebuilt, git, reason in cases:
            with self.subTest(reason=reason), \
                    mock.patch(REBUILT, **({"side_effect": rebuilt} if isinstance(rebuilt, Exception)
                                          else {"return_value": rebuilt})), \
                    mock.patch(GIT, **({"side_effect": git} if isinstance(git, Exception)
                                      else {"return_value": git})):
                data, basis = rs.run_schema_bytes(record)
            self.assertIsNone(data)
            self.assertEqual((basis["source"], basis["path"], basis["sha256"]),
                             (rs.TODAY, "src/x_all.yaml", "a" * 64))
            self.assertIn(reason, basis["reason"])

    def test_an_oserror_resolving_the_path_on_disk_goes_on_to_the_next_source(self):
        """The one difference from the code `run_enum_aliases` held: there
        `resource_path` ran outside the `try`, so an OSError resolving the
        path (a deleted working directory, an unsearchable `src/`) raised
        out of removals. Here it is a file not on disk, and the
        reconstruction and git are asked."""
        record = {"schema": {"full_path": "src/x_all.yaml", "full_sha256": "a" * 64}}
        for error in (FileNotFoundError(2, "No such file or directory"),
                      PermissionError(13, "Permission denied", "src")):
            with self.subTest(error=type(error).__name__), \
                    mock.patch("data_sheets_schema.resources.resource_path", side_effect=error), \
                    mock.patch(REBUILT, return_value=None) as rebuilt, \
                    mock.patch(GIT, return_value=(b"bytes", {"commit": "c" * 40, "matched_on": ["sha256"]})):
                data, basis = rs.run_schema_bytes(record)
            rebuilt.assert_called_once()
            self.assertEqual((data, basis["source"], basis["commit"]),
                             (b"bytes", "the run's schema, a git blob", "c" * 40))

    def test_removals_reads_its_enum_tables_through_the_helper(self):
        """The extraction: `run_enum_aliases` is the helper's bytes and basis,
        tabled, or None with the helper's fallback basis."""
        from data_sheets_schema import removals as rm
        data = yaml.safe_dump({"enums": {"E": {"permissible_values": {"bar": {"aliases": ["Foo"]}}}},
                               "classes": {"C": {"attributes": {"kind": {"range": "E"}}}}}).encode()
        basis = {"source": "the run's schema, a git blob", "path": "p", "sha256": "s"}
        with mock.patch("data_sheets_schema.run_schema.run_schema_bytes", return_value=(data, basis)) as got:
            tables, said = rm.run_enum_aliases({"schema": {}})
        got.assert_called_once_with({"schema": {}})
        self.assertEqual((tables, said), ({"kind": {"Foo": "bar", "foo": "bar", "bar": "bar"}}, basis))
        fallback = {"source": rs.TODAY, "reason": "why"}
        with mock.patch("data_sheets_schema.run_schema.run_schema_bytes", return_value=(None, fallback)):
            self.assertEqual(rm.run_enum_aliases(None), (None, fallback))


class Rules(unittest.TestCase):
    """`identifier_rules`: the rules of the run's bytes, by today's functions."""

    def test_the_rules_of_other_bytes_are_read_as_todays_are(self):
        """The same derivation on other bytes: today's file through the
        private view gives exactly what today's functions give."""
        from data_sheets_schema.identifiers import FULL_SCHEMA
        from data_sheets_schema.resources import resource_path
        self.assertEqual(rs._derive_rules(resource_path(FULL_SCHEMA).read_bytes()), rs.todays_identifier_rules())

    def test_a_run_schema_s_rules_are_its_own(self):
        rules = rs._derive_rules(yaml.safe_dump(RUN_SCHEMA).encode())
        self.assertEqual(rules, rs.IdentifierRules(
            prefixes=frozenset({"foo", "linkml"}), slots=frozenset({"id", "publisher"}),
            persons=frozenset({"lead"}),
            bases=(("https://foo.example.org/", "foo"), ("https://w3id.org/linkml/", "linkml"))))

    def test_a_slot_only_the_run_schema_ranges_on_uriorcurie_is_among_its_identifier_slots(self):
        """The premise of the `unit` tests below (#4081): the run's rules
        walk `unit` and today's do not. If a release ranges `unit` on
        `uriorcurie` again, those tests need a slot today's does not."""
        from data_sheets_schema.identifiers import uriorcurie_slots
        self.assertEqual(rs._derive_rules(yaml.safe_dump(UNIT_SCHEMA).encode()).slots,
                         frozenset({"id", "publisher", "unit"}))
        self.assertNotIn("unit", uriorcurie_slots())

    def test_rules_are_derived_once_per_version(self):
        data = yaml.safe_dump({**RUN_SCHEMA, "name": "derived-once"}).encode()
        rs._RULES_BY_SHA256.pop(hashlib.sha256(data).hexdigest(), None)
        with mock.patch.object(rs, "_derive_rules", wraps=rs._derive_rules) as derive:
            first, second = rs._rules_of(data), rs._rules_of(data)
        self.assertIs(first, second)
        derive.assert_called_once_with(data)

    def test_rules_fall_back_to_todays_with_the_reason(self):
        with mock.patch(REBUILT, return_value=None), mock.patch(GIT, return_value=None):
            rules, basis = rs.identifier_rules({"schema": {"full_path": "src/x_all.yaml", "full_md5": "m"}})
        self.assertEqual(rules, rs.todays_identifier_rules())
        self.assertEqual(basis["source"], rs.TODAY)

    def test_bytes_that_import_a_local_file_are_the_stated_fallback(self):
        """A merged schema imports nothing. An import would be read from
        today's tree, which the recorded hash does not cover."""
        today = rs.IdentifierRules(frozenset({"today"}), frozenset(), frozenset(), ())
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(rs, "todays_identifier_rules", return_value=today):
            path, sha, _md5 = _schema_file(tmp, {**RUN_SCHEMA, "imports": ["linkml:types", "D4D_Base_import"]})
            rules, basis = rs.identifier_rules({"schema": {"full_path": str(path), "full_sha256": sha}})
        self.assertIs(rules, today)
        self.assertEqual((basis["source"], basis["path"], basis["sha256"]), (rs.TODAY, str(path), sha))
        self.assertIn('the bytes recovered as "the run\'s schema, on disk" could not be loaded as a schema',
                      basis["reason"])
        self.assertIn("import D4D_Base_import", basis["reason"])


class VersionView(unittest.TestCase):
    """`schema_view.version_view`: a view of a version read by its hash, for
    one `with` block. It is never shared, so it never evicts today's view of
    the same path (#926: an evicted view of today's schema would be rebuilt,
    and pinned again, for each version). Its method caches are its own, so
    once released it is freed (#4082: kept for the process, each version
    view was 24-49 MB resident, and a corpus pass meets 14 versions)."""

    def test_a_version_view_is_not_shared_and_never_evicts_todays_view(self):
        from data_sheets_schema import schema_view
        from data_sheets_schema.identifiers import FULL_SCHEMA
        today = schema_view.shared_view(FULL_SCHEMA)
        held = schema_view.views_held()
        doc = schema_view.version_document(yaml.safe_dump({**RUN_SCHEMA, "name": "a-recorded-version"}).encode())
        with schema_view.version_view(FULL_SCHEMA, doc) as view:
            self.assertEqual(view.schema.name, "a-recorded-version")
            self.assertEqual(str(view.induced_slot("publisher", "Dataset").range), "uriorcurie")
            self.assertEqual(schema_view.views_held(), held)
        self.assertIs(schema_view.shared_view(FULL_SCHEMA), today)
        self.assertEqual(schema_view.views_held(), held)

    def test_a_released_version_view_is_freed(self):
        """Its cached methods have run, which pins a view whose caches are
        linkml's class-level ones. This one goes with its last reference,
        with no collection, once its block has exited. That includes a
        deprecated alias, whose `deprecated` wrapper sits outside the cache."""
        from data_sheets_schema import schema_view
        from data_sheets_schema.identifiers import FULL_SCHEMA, person_slots_of, uriorcurie_slots_of
        doc = schema_view.version_document(yaml.safe_dump({**RUN_SCHEMA, "name": "released"}).encode())
        with schema_view.version_view(FULL_SCHEMA, doc) as view:
            self.assertEqual((uriorcurie_slots_of(view), person_slots_of(view)), ({"id", "publisher"}, {"lead"}))
            self.assertIn("Dataset", view.all_class())
            freed = weakref.ref(view)
        del view
        self.assertIsNone(freed(), "a released version view is still referenced")

    def test_every_class_cached_method_is_cached_on_the_instance(self):
        """Each of linkml's class-level caches is shadowed by one on the
        instance, of the function the cache wraps, never of the cache
        itself: a class-level cache anywhere in the chain pins the view."""
        from linkml_runtime import SchemaView

        from data_sheets_schema import schema_view
        cached = {name for name, attr in vars(SchemaView).items() if hasattr(attr, "cache_info")}
        self.assertTrue(cached)
        self.assertEqual(set(schema_view._INSTANCE_CACHED), cached)
        for name in sorted(cached):
            shadow = vars(schema_view._ReleasableView)[name]
            self.assertIsInstance(shadow, schema_view._InstanceCached, name)
            self.assertFalse(hasattr(shadow.function, "cache_info"), name)

    def test_a_version_view_serves_a_repeated_call_from_its_instance_cache(self):
        """The caching itself, not only its shape (#4114): a second call of a
        cached method on a version view is a hit on a cache stored in the
        view's own `__dict__`, and returns the first call's object. Without
        it every call recomputes, and deriving one version's rules takes
        minutes instead of a second."""
        from data_sheets_schema import schema_view
        from data_sheets_schema.identifiers import FULL_SCHEMA
        doc = schema_view.version_document(yaml.safe_dump({**RUN_SCHEMA, "name": "cached"}).encode())
        with schema_view.version_view(FULL_SCHEMA, doc) as view:
            first = view.all_classes()
            cache = view.__dict__.get("all_classes")
            self.assertIsNotNone(cache, "all_classes is not cached on the instance")
            self.assertIs(view.all_classes(), first)
            self.assertGreaterEqual(cache.cache_info().hits, 1)

    def test_a_modified_version_view_reads_its_modification(self):
        """linkml's caches miss once a view is modified, since `set_modified`
        moves the hash in every key. A version view's caches are keyed on
        the arguments alone, so a modification drops them, and the view
        reads what a SchemaView reads."""
        from linkml_runtime import SchemaView
        from linkml_runtime.linkml_model.meta import ClassDefinition, SchemaDefinition, SlotDefinition

        from data_sheets_schema import schema_view
        from data_sheets_schema.identifiers import FULL_SCHEMA, uriorcurie_slots_of

        def extra():
            return ClassDefinition("Extra", attributes={"code": SlotDefinition("code", range="uriorcurie")})
        plain = SchemaView(SchemaDefinition(**schema_view.version_document(yaml.safe_dump(RUN_SCHEMA).encode())))
        self.assertEqual(uriorcurie_slots_of(plain), {"id", "publisher"})
        plain.add_class(extra())
        self.assertEqual(uriorcurie_slots_of(plain), {"id", "publisher", "code"})
        doc = schema_view.version_document(yaml.safe_dump({**RUN_SCHEMA, "name": "modified"}).encode())
        with schema_view.version_view(FULL_SCHEMA, doc) as view:
            self.assertEqual(uriorcurie_slots_of(view), {"id", "publisher"})
            view.add_class(extra())
            self.assertEqual(set(view.all_classes()), {"Dataset", "Person", "Extra"})
            self.assertEqual(uriorcurie_slots_of(view), {"id", "publisher", "code"})

    def test_deriving_a_version_s_rules_keeps_no_view(self):
        """`run_schema` keeps a version's rules and not the view it read them
        from, so a corpus pass holds one version view at a time (#4082)."""
        from data_sheets_schema import schema_view
        real, seen = schema_view.version_view, []

        @contextmanager
        def watched(path, document):
            with real(path, document) as view:
                seen.append(weakref.ref(view))
                yield view
        with mock.patch.object(schema_view, "version_view", watched):
            rules = rs._derive_rules(yaml.safe_dump({**RUN_SCHEMA, "name": "keeps-no-view"}).encode())
        self.assertEqual(rules.slots, frozenset({"id", "publisher"}))
        self.assertEqual(len(seen), 1)
        self.assertIsNone(seen[0](), "the rules were read and the view outlived them")

    def test_only_a_mapping_importing_at_most_the_linkml_metamodel_is_viewed(self):
        from data_sheets_schema import schema_view
        from data_sheets_schema.identifiers import FULL_SCHEMA
        with self.assertRaisesRegex(ValueError, "the bytes are not a schema mapping"):
            schema_view.version_document(b"- a\n- list\n")
        with self.assertRaisesRegex(ValueError, "import D4D_Base_import, which their recorded hash"):
            with schema_view.version_view(FULL_SCHEMA, {**RUN_SCHEMA, "imports": ["linkml:types", "D4D_Base_import"]}):
                pass
        doc = schema_view.version_document(yaml.safe_dump(
            {**RUN_SCHEMA, "name": "imports-the-metamodel", "imports": ["linkml:types"]}).encode())
        with schema_view.version_view(FULL_SCHEMA, doc) as view:
            self.assertEqual(str(view.induced_slot("id", "Dataset").range), "uriorcurie")


class FormBlock(unittest.TestCase):
    """The undeclared-prefix count reads the run's declared prefixes, its
    Person slots and its identifier slots, and so does the organisational-
    fragment count, which walks the same slots. The block says which schema
    it read."""

    def _records(self, tmp: str, full: dict) -> tuple[Path, Path]:
        paths = Path(tmp) / "P_d4d.yaml", Path(tmp) / "P_d4d_core.yaml"
        paths[0].write_text(yaml.safe_dump(full), encoding="utf-8")
        return paths

    def test_the_counts_walk_the_run_schema_s_identifier_slots(self):
        """#4081: the run's schema ranged `unit` on `uriorcurie` and today's
        does not. A CURIE in `unit` is a prefix the run's schema did not
        declare, and a ROR with a fragment there is an organisational
        fragment. A walk of today's slots sees neither."""
        from data_sheets_schema.grounding import form_facts
        with tempfile.TemporaryDirectory() as tmp:
            path, sha, _md5 = _schema_file(tmp, UNIT_SCHEMA)
            full, core = self._records(tmp, {"id": "foo:1", "variables": [
                {"name": "weight", "unit": "qudt:Kilogram"},
                {"name": "site", "unit": "ROR:032db5x82#bench"}]})
            run = form_facts(full, core, record={"schema": {"full_path": str(path), "full_sha256": sha}})
            today = form_facts(full, core)
        self.assertEqual(run["undeclared_prefixes"], {"qudt": 1, "ROR": 1})
        self.assertEqual(run["organisational_fragments"], 1)
        self.assertEqual(run["schema_basis"]["source"], "the run's schema, on disk")
        # Today's walk reaches `id` only, whose `foo` today's schema does not declare.
        self.assertEqual(today["undeclared_prefixes"], {"foo": 1})
        self.assertEqual(today["organisational_fragments"], 0)

    def test_the_prefix_count_reads_the_run_schema(self):
        from data_sheets_schema.grounding import form_facts
        with tempfile.TemporaryDirectory() as tmp:
            path, sha, _md5 = _schema_file(tmp)
            full, core = self._records(tmp, {"id": "foo:1", "publisher": "doi:10.1/x",
                                             "lead": {"id": "mailto:jane@example.org"}})
            record = {"schema": {"full_path": str(path), "full_sha256": sha}}
            run = form_facts(full, core, record=record)
            today = form_facts(full, core)
        # The run's schema declared `foo` and not `doi`, and ranged `lead` on
        # Person, so its `mailto:` id is the normaliser's case (#982 v3).
        self.assertEqual(run["undeclared_prefixes"], {"doi": 1})
        self.assertEqual(run["schema_basis"], {"source": "the run's schema, on disk", "path": str(path),
                                               "sha256": sha})
        # Today's declares `doi` and not `foo`, and ranges no `lead` on Person.
        self.assertEqual(today["undeclared_prefixes"], {"foo": 1, "mailto": 1})
        self.assertNotIn("schema_basis", today)

    def test_no_record_on_disk_reads_no_schema(self):
        from data_sheets_schema.grounding import form_facts
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(rs, "identifier_rules", side_effect=AssertionError("not asked")):
            out = form_facts(Path(tmp) / "a.yaml", Path(tmp) / "b.yaml", record={"schema": {}})
        self.assertEqual(out, {"checked": False, "reason": "neither record is on disk"})

    def test_git_that_cannot_be_started_is_todays_count_with_its_reason(self):
        from data_sheets_schema.grounding import form_facts
        with tempfile.TemporaryDirectory() as tmp:
            full, core = self._records(tmp, {"id": "foo:1"})
            record = {"schema": {"full_path": "src/data_sheets_schema/schema/gone_all.yaml", "full_sha256": "a" * 64}}
            with mock.patch(REBUILT, return_value=None), \
                    mock.patch(GIT, side_effect=FileNotFoundError(2, "No such file or directory", "git")):
                out = form_facts(full, core, record=record)
        self.assertEqual(out["undeclared_prefixes"], {"foo": 1})
        self.assertEqual(out["schema_basis"]["source"], rs.TODAY)
        self.assertIn("git could not be run (FileNotFoundError", out["schema_basis"]["reason"])

    def test_the_voice_v4_rep1_run_read_prefixes_its_commits_blob_lacks(self):
        """#3788 on the record: the run's schema, read from its committed
        artefact, declares `ROR`, `ORCID` and `doi`; the blob at its commit
        (the artefact less the edit, the bytes the other runs of that label
        recorded) declares none of them. A `ROR:` CURIE is undeclared only
        against the wrong bytes."""
        from data_sheets_schema.backfill_checks import record_paths
        from data_sheets_schema.grounding import form_facts, undeclared_prefixes
        from data_sheets_schema.provenance import _REPO_ROOT
        from data_sheets_schema.reconstructed_bytes import RECONSTRUCTIONS
        label = _REPO_ROOT / "data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1"
        prov, sibling = label / "VOICE_provenance.yaml", label / "AI_READI_provenance.yaml"
        if not (prov.exists() and sibling.exists()):
            self.skipTest("needs the corpus records")
        record = yaml.safe_load(prov.read_text(encoding="utf-8"))
        with mock.patch(GIT, side_effect=AssertionError("git must not be needed")):
            rules, basis = rs.identifier_rules(record)
        self.assertEqual((basis["source"], basis["artefact"]),
                         ("the run's schema, reconstructed", RECONSTRUCTIONS[0]["artefact"]))
        self.assertLessEqual({"ROR", "ORCID", "doi"}, rules.prefixes)
        (edit,) = RECONSTRUCTIONS[0]["edits"]
        lines = gzip.decompress((_REPO_ROOT / RECONSTRUCTIONS[0]["artefact"]).read_bytes()).splitlines(keepends=True)
        blob = b"".join(lines[:edit["at"]] + lines[edit["at"] + edit["insert"].count("\n"):])
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         yaml.safe_load(sibling.read_text(encoding="utf-8"))["schema"]["full_sha256"])
        blob_rules = rs._rules_of(blob)
        self.assertFalse({"ROR", "ORCID", "doi"} & blob_rules.prefixes)
        ror = {"id": "ROR:032db5x82"}
        self.assertEqual(undeclared_prefixes(ror, {"id"}, prefixes=rules.prefixes, persons=rules.persons), {})
        self.assertEqual(undeclared_prefixes(ror, {"id"}, prefixes=blob_rules.prefixes,
                                             persons=blob_rules.persons), {"ROR": 1})
        paths = record_paths(prov)
        self.assertEqual(form_facts(paths["full"], paths["core"], record=record)["schema_basis"], basis)


class GroundingBlock(unittest.TestCase):
    """The identifier walk reads the run's identifier slots, and the
    resolver-URL finding reads them and the run's declared bases."""

    def test_the_identifier_walk_reads_the_run_schema_s_slots(self):
        """#4081: the run's schema ranged `unit` on `uriorcurie` and today's
        does not. A DOI in `unit` that the bundle lacks is absent, and a URL
        on a base the run's schema declared is a resolver-URL finding. A walk
        of today's slots sees neither."""
        from data_sheets_schema.grounding import check_run
        with tempfile.TemporaryDirectory() as tmp:
            path, sha, _md5 = _schema_file(tmp, UNIT_SCHEMA)
            full = Path(tmp) / "P_d4d.yaml"
            full.write_text(yaml.safe_dump({"id": "doi:10.1234/x", "variables": [
                {"name": "dose", "unit": "doi:10.5555/not-in-the-bundle"},
                {"name": "site", "unit": "https://foo.example.org/unit/7"}]}), encoding="utf-8")
            bundle = Path(tmp) / "bundle.txt"
            bundle.write_text("The dataset is doi.org/10.1234/x.\n", encoding="utf-8")
            record = {"schema": {"full_path": str(path), "full_sha256": sha}}
            run = check_run(full, Path(tmp) / "P_d4d_core.yaml", bundle, record=record)
            today = check_run(full, Path(tmp) / "P_d4d_core.yaml", bundle)
        self.assertEqual(run["counts"], {"grounded": 1, "minted_fragment": 0, "absent": 1})
        self.assertEqual(run["distinct"], {"grounded": 1, "minted_fragment": 0, "absent": 1})
        self.assertEqual(sorted((f["kind"], f["path"], f.get("identifier") or f.get("value"))
                                for f in run["findings"]),
                         [("identifier_not_in_bundle", "$.variables[].unit", "10.5555/not-in-the-bundle"),
                          ("resolver_url_in_identifier_slot", "$.variables[].unit",
                           "https://foo.example.org/unit/7")])
        self.assertEqual(today["counts"], {"grounded": 1, "minted_fragment": 0, "absent": 0})
        self.assertEqual(today["distinct"], {"grounded": 1, "minted_fragment": 0, "absent": 0})
        self.assertEqual(today["findings"], [])

    def test_the_resolver_url_finding_reads_the_run_schema_bases(self):
        """Where the run's schema declared no `doi`, its resolver URL was the
        only form the run could write: not a finding. A URL on a base it did
        declare is."""
        from data_sheets_schema.grounding import check_run
        with tempfile.TemporaryDirectory() as tmp:
            path, sha, _md5 = _schema_file(tmp)
            full = Path(tmp) / "P_d4d.yaml"
            full.write_text(yaml.safe_dump({"id": "https://doi.org/10.1234/x",
                                            "publisher": "https://foo.example.org/thing"}), encoding="utf-8")
            bundle = Path(tmp) / "bundle.txt"
            bundle.write_text("The dataset is doi.org/10.1234/x.\n", encoding="utf-8")
            record = {"schema": {"full_path": str(path), "full_sha256": sha}}
            run = check_run(full, Path(tmp) / "P_d4d_core.yaml", bundle, record=record)
            today = check_run(full, Path(tmp) / "P_d4d_core.yaml", bundle)

        def urls(block):
            return [(f["prefix"], f["value"]) for f in block["findings"]
                    if f["kind"] == "resolver_url_in_identifier_slot"]
        self.assertEqual(urls(run), [("foo", "https://foo.example.org/thing")])
        self.assertEqual(urls(today), [("doi", "https://doi.org/10.1234/x")])
        self.assertEqual(run["counts"], today["counts"])
        self.assertEqual(run["counts"]["grounded"], 1)
        self.assertEqual(run["schema_basis"]["source"], "the run's schema, on disk")
        self.assertNotIn("schema_basis", today)


class Backfill(unittest.TestCase):
    """`backfill_checks.compute` (and so `d4d provenance record`) passes the
    provenance record to both blocks, and the report line names a fallback."""

    def _layout(self, tmp: str, schema: dict) -> Path:
        owner = Path(tmp)
        provenance = owner / "data/d4d_concatenated/external_core/run/P_provenance.yaml"
        provenance.parent.mkdir(parents=True)
        schema_path, sha, _md5 = _schema_file(tmp)
        provenance.write_text(yaml.safe_dump({"inputs": {"bundle_path": "evidence.txt"},
                                              "schema": {"full_path": str(schema_path), "full_sha256": sha,
                                                         **schema}}), encoding="utf-8")
        from data_sheets_schema.backfill_checks import record_paths
        for name in ("full", "core"):
            target = record_paths(provenance)[name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("id: foo:1\npublisher: https://foo.example.org/thing\n", encoding="utf-8")
        (owner / "evidence.txt").write_text("No identifier is stated here.\n", encoding="utf-8")
        return provenance

    def test_compute_reads_the_run_schema_for_form_and_grounding(self):
        from data_sheets_schema.backfill_checks import compute, summarise
        with tempfile.TemporaryDirectory() as tmp:
            blocks = compute(self._layout(tmp, {}), only={"form", "grounding"})
        for name in ("form", "grounding"):
            self.assertEqual(blocks[name]["schema_basis"]["source"], "the run's schema, on disk", name)
        self.assertEqual(blocks["form"]["undeclared_prefixes"], {})
        self.assertEqual([f["prefix"] for f in blocks["grounding"]["findings"]
                          if f["kind"] == "resolver_url_in_identifier_slot"], ["foo", "foo"])
        self.assertNotIn(rs.TODAY, summarise(blocks))

    def test_a_fallback_is_named_on_the_report_line(self):
        from data_sheets_schema.backfill_checks import compute, summarise
        with tempfile.TemporaryDirectory() as tmp:
            provenance = self._layout(tmp, {"full_sha256": "0" * 64})
            with mock.patch(REBUILT, return_value=None), \
                    mock.patch(GIT, side_effect=GitUnavailable("shallow clone")):
                blocks = compute(provenance, only={"form", "grounding"})
        for name in ("form", "grounding"):
            self.assertEqual(blocks[name]["schema_basis"]["source"], rs.TODAY, name)
        self.assertEqual(blocks["form"]["undeclared_prefixes"], {"foo": 2})
        self.assertIn("today's schema read: the run's schema is not on disk and git cannot answer "
                      "(shallow clone)", summarise(blocks))

    def test_either_block_alone_names_its_fallback_on_the_report_line(self):
        """`--blocks form` or `--blocks grounding` computes one block, and
        that block's fallback is on the report line by itself (#4081)."""
        from data_sheets_schema.backfill_checks import compute, summarise
        for only in ({"form"}, {"grounding"}):
            with self.subTest(only=only), tempfile.TemporaryDirectory() as tmp:
                provenance = self._layout(tmp, {"full_sha256": "0" * 64})
                with mock.patch(REBUILT, return_value=None), \
                        mock.patch(GIT, side_effect=GitUnavailable("shallow clone")):
                    blocks = compute(provenance, only=only)
                self.assertEqual(set(blocks), only)
                self.assertIn("today's schema read: the run's schema is not on disk and git cannot "
                              "answer (shallow clone)", summarise(blocks))


if __name__ == "__main__":
    unittest.main()
