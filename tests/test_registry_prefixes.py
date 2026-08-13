"""Our B2AI_* prefixes match the registry's (#535).

All three previously pointed at the registry's *homepage* URL,
`https://w3id.org/bridge2ai/b2ai-standards-registry/`, while the registry
declares per-schema namespaces. So `B2AI_TOPIC:x` in one of our records and
`B2AI_TOPIC:x` in the registry were **different IRIs**.

That is worse than an undeclared prefix. `d4d runs identifiers` reports an
undeclared prefix as unresolvable, which is honest; a prefix bound to the wrong
namespace resolves — somewhere else — and the audit passes it, because the CURIE
is well-formed and the prefix *is* declared. It is #402's finding one level up:
the audit checked that a prefix was declared, never that it was declared
correctly, because there was nothing to check it against.

There is now. The registry's declarations are pinned in
`b2ai_registry_prefixes.yaml` with the commit they were taken at, and this
compares the schema against that pin. Deliberately offline: a refresh is an
edit to the pin, with a diff a reviewer reads, rather than a silent network
dependency that turns a registry change into a surprise CI failure.
"""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src/data_sheets_schema/schema/data_sheets_schema.yaml"
PIN = ROOT / "src/data_sheets_schema/b2ai_registry_prefixes.yaml"


def _schema_prefixes():
    doc = yaml.safe_load(SCHEMA.read_text(encoding="utf-8")) or {}
    return doc.get("prefixes") or {}


def _pin():
    return yaml.safe_load(PIN.read_text(encoding="utf-8")) or {}


class TestOursMatchTheRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ours = _schema_prefixes()
        cls.pin = _pin()

    def test_every_registry_prefix_is_declared_here(self):
        for name in self.pin["prefixes"]:
            with self.subTest(prefix=name):
                self.assertIn(name, self.ours,
                              f"{name} is declared by the registry and not here")

    def test_each_expands_to_the_registry_namespace(self):
        """The bug itself. A prefix that expands differently makes two systems
        disagree about what one CURIE names, undetectably."""
        for name, namespace in self.pin["prefixes"].items():
            with self.subTest(prefix=name):
                self.assertEqual(self.ours.get(name), namespace)

    def test_no_b2ai_prefix_points_at_the_registry_homepage(self):
        """The specific mistake: binding a prefix to the site rather than to
        the namespace. `B2AI_STANDARD` is exempt and declared local."""
        homepage = "https://w3id.org/bridge2ai/b2ai-standards-registry/"
        local = set(self.pin.get("local_only") or {})
        for name, value in self.ours.items():
            if not name.startswith("B2AI_") or name in local:
                continue
            with self.subTest(prefix=name):
                self.assertNotEqual(value, homepage)


class TestLocalPrefixesAreDeclaredAsSuch(unittest.TestCase):
    """A prefix we invent is fine; a prefix we invent *silently* is how this
    started. `local_only` is the difference between "ours, deliberately" and
    "drifted from theirs"."""

    @classmethod
    def setUpClass(cls):
        cls.ours = _schema_prefixes()
        cls.pin = _pin()

    def test_every_b2ai_prefix_is_either_registry_or_declared_local(self):
        known = set(self.pin["prefixes"]) | set(self.pin.get("local_only") or {})
        ours = {n for n in self.ours if n.startswith("B2AI_")}
        self.assertEqual(ours - known, set(),
                         "a B2AI_ prefix that is neither the registry's nor "
                         "recorded as local")

    def test_local_entries_say_why(self):
        for name, why in (self.pin.get("local_only") or {}).items():
            with self.subTest(prefix=name):
                self.assertGreater(len(str(why)), 40,
                                   f"{name} is local with no reason given")


class TestThePinIsTraceable(unittest.TestCase):
    """A pin without provenance is a hardcoded list with extra steps."""

    def test_it_names_the_source_and_the_commit(self):
        source = _pin().get("source") or {}
        for field in ("repository", "path", "commit"):
            with self.subTest(field=field):
                self.assertTrue(source.get(field))

    def test_the_commit_looks_like_a_sha(self):
        self.assertRegex(str((_pin()["source"])["commit"]), r"^[0-9a-f]{40}$")
