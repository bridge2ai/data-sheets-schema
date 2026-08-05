"""Every field a rubric20 scorer names must exist in the schema (#319).

#316 aligned the scorers' question *names* with `data/rubric/rubric20.txt`.
Their `field:` lists were still written against a schema the project no longer
has. Measured across the 25 current records, 29 of the 93 distinct paths named
by the rubric or a scorer could not resolve from `Dataset` at all.

A field that does not resolve does not fail — it reads as absent, forever. Two
questions were therefore unscoreable on every record ever produced:

    Q5   Data File Size Availability     0/1 on all 25 records
    Q10  Interoperability ...            0/5 on all 25 records

Q10 also carried a plain type bug — `formats_str = str(has_formats)` stringified
a *bool*, so no format name was ever found in `"True"`. Six of 88 points were
unreachable regardless of what a record contained.

The distinction this file rests on: a path that **cannot resolve** produces a
meaningless 0, and a path that **resolves but is empty** produces a true one.
`regulatory_restrictions.confidentiality_level` is the second kind — no current
record fills it, Q9 scores 3 on all 25, and that is a real finding about the
records rather than a broken scorer. Bare `confidentiality_level` was the first
kind, and reported the same number for the wrong reason.

So the test is resolution, not population. It would be wrong to require every
named field to appear in some record — that would forbid the rubric from asking
for anything the generator does not yet produce, which is most of what a rubric
is for.
"""

import functools
import importlib.util
import json
import re
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.constants.evaluation import RUBRIC20_PATH

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"
HYBRID = REPO / "scripts" / "batch_evaluate_rubric20_hybrid.py"
AGENTS = {
    "rubric20": REPO / ".claude" / "agents" / "d4d-rubric20.md",
    "rubric20-semantic": REPO / ".claude" / "agents" / "d4d-rubric20-semantic.md",
}


@functools.lru_cache(maxsize=1)
def _view():
    from linkml_runtime import SchemaView
    return SchemaView(str(SCHEMA))


@functools.lru_cache(maxsize=None)
def _slots(class_name):
    try:
        return {s.name: s for s in _view().class_induced_slots(class_name)}
    except Exception:
        return {}


def resolves(path, start="Dataset"):
    """Walk a dotted path from `start`, as a scorer reading a record would."""
    cls = start
    parts = path.split(".")
    for i, part in enumerate(parts):
        slots = _slots(cls)
        if part not in slots:
            return False
        if i < len(parts) - 1:
            rng = slots[part].range
            if not _view().get_class(rng):
                return False
            cls = rng
    return True


def _json_keys(node):
    """Every key name in a JSON document, at any depth."""
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _json_keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _json_keys(v)}
    return set()


def _rubric():
    return yaml.safe_load(Path(RUBRIC20_PATH).read_text())[
        "d4d_evaluation_rubric"]["rubric"]


def _question(number):
    return next(q for q in _rubric() if q["id"] == number)


def _hybrid():
    spec = importlib.util.spec_from_file_location("rubric20_hybrid", HYBRID)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _agent_fields(path):
    """`**Fields:**` per question, keyed by the nearest preceding heading."""
    out, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^#### Question (\d+): ", line)
        if heading:
            current = int(heading.group(1))
            continue
        fields = re.match(r"^\*\*Fields:\*\* (.+?)\s*$", line)
        if fields and current is not None:
            out[current] = re.findall(r"`([^`]+)`", fields.group(1))
            current = None
    return out


class TestThePremise(unittest.TestCase):
    """`resolves` has to be able to say no, or every test below is vacuous."""

    def test_a_real_top_level_slot_resolves(self):
        self.assertTrue(resolves("license_and_use_terms"))

    def test_a_real_nested_path_resolves(self):
        self.assertTrue(resolves("regulatory_restrictions.confidentiality_level"))

    def test_a_leaf_without_its_path_does_not(self):
        """This is the whole defect in one line: `confidentiality_level` is a
        real field, on a class that is not `Dataset`."""
        self.assertFalse(resolves("confidentiality_level"))

    def test_an_invented_slot_does_not(self):
        self.assertFalse(resolves("data_characteristics"))
        self.assertFalse(resolves("software_and_tools"))


class TestTheRubricResolves(unittest.TestCase):
    """The rubric is the source: `rubric20_system_prompt.md` interpolates it
    into the API judge, so a dead field there reaches every scorer at once."""

    def test_every_field_the_rubric_names_resolves(self):
        for question in _rubric():
            for name in question.get("field") or []:
                with self.subTest(question=question["id"], field=name):
                    self.assertTrue(
                        resolves(name),
                        f"Q{question['id']} scores `{name}`, which cannot be "
                        "reached from Dataset — it reads as absent forever")

    def test_every_question_names_at_least_one_field(self):
        for question in _rubric():
            with self.subTest(question=question["id"]):
                self.assertTrue(question.get("field"),
                                "a question with no fields cannot be scored")


class TestFieldsMatchWhatTheQuestionMeasures(unittest.TestCase):
    """Resolution is necessary and not sufficient.

    One dead name does not have one replacement. `format` in Q4 — a count of
    file *types*, scored "1 type / 2-3 / >3" — is not `format` in Q10, which is
    about schema conformance. Remapping both to the same thing gave Q4 a schema
    URL and two byte-size fields: every path resolved, every existing test
    passed, and the question no longer measured what its own `method:` and
    scoring bands say it measures.

    Caught in review of the change that caused it. These two questions are the
    pair most easily conflated, so they are pinned by concept rather than by a
    literal list — a scorer may add fields, but not swap which of the two it is.
    """

    SIZE = {"total_size_bytes", "file_collections.total_bytes"}
    ENUMERATION = {"distribution_formats", "file_collections", "total_file_count"}

    def test_the_type_variety_question_does_not_score_sizes(self):
        """Q4 counts types; a byte total says nothing about how many."""
        fields = set(_question(4)["field"])
        self.assertEqual(fields & self.SIZE, set())
        self.assertTrue(fields & self.ENUMERATION)

    def test_the_file_size_question_does_score_sizes(self):
        """The complement, so the rule above cannot be satisfied by emptying
        both lists."""
        self.assertTrue(set(_question(5)["field"]) & self.SIZE)

    def test_the_interoperability_question_scores_schema_conformance(self):
        """Q10 is where `conforms_to_schema` belongs."""
        self.assertIn("conforms_to_schema", _question(10)["field"])


@unittest.skipUnless(HYBRID.exists(), "hybrid scorer not present")
class TestTheScorersResolve(unittest.TestCase):

    def test_every_field_the_hybrid_scorer_names_resolves(self):
        for q, spec in _hybrid().RUBRIC20_QUESTIONS.items():
            for name in spec["fields"]:
                with self.subTest(question=q, field=name):
                    self.assertTrue(resolves(name), f"Q{q} scores `{name}`")

    def test_every_field_the_agents_name_resolves(self):
        for agent, path in AGENTS.items():
            for q, fields in _agent_fields(path).items():
                for name in fields:
                    with self.subTest(agent=agent, question=q, field=name):
                        self.assertTrue(resolves(name), f"Q{q} scores `{name}`")

    def test_the_scorers_cover_the_rubrics_fields(self):
        """A scorer may add fields; it may not quietly drop the rubric's.

        Dropping is how a question keeps its name while scoring something
        narrower, which is the drift #316 fixed at the level of names.
        """
        rubric = {q["id"]: set(q.get("field") or []) for q in _rubric()}
        tables = {"hybrid": {q: set(s["fields"])
                             for q, s in _hybrid().RUBRIC20_QUESTIONS.items()}}
        for agent, path in AGENTS.items():
            tables[agent] = {q: set(f) for q, f in _agent_fields(path).items()}
        for who, table in tables.items():
            for q, want in rubric.items():
                with self.subTest(scorer=who, question=q):
                    self.assertEqual(want - table.get(q, set()), set())


class TestTheAgentsProse(unittest.TestCase):
    """`**Fields:**` is not the only place the agents name record fields.

    The cross-field consistency rules name them too — "IF
    `human_subject_research.involves_human_subjects=True` THEN EXPECT
    `ethical_reviews` populated". A dead name there tells the judge to compare
    against something that cannot exist, and no test of the Fields lines can
    see it. A mutation check found this gap: swapping
    `participant_privacy.reidentification_risk` for the bare leaf in a
    consistency rule left every other test green.

    Backticked snake_case tokens that are *not* record fields — the agent's own
    output keys and the filenames it writes — are excluded by provenance rather
    than by a hand-maintained list: they are read from the two JSON contracts
    the agent emits against.
    """

    #: Names of artifacts the agent writes, which are neither record fields nor
    #: output keys. Small and closed, so a literal is honest here.
    ARTIFACTS = {"all_scores.csv", "evaluation_summary.yaml", "summary_report.md"}

    #: Output keys of the N/A convention. These *should* come from
    #: `rubric20_semantic_schema.json` with the rest, and do not, because that
    #: schema still declares the pre-N/A shape — it requires `percentage`, which
    #: the agent no longer emits, and all 28 recorded semantic evaluations fail
    #: it. Listed here rather than silently widened so the gap stays visible.
    #: See #323.
    UNDECLARED_OUTPUT_KEYS = {
        "adjusted_max_points", "excluded_max_points", "normalized_percentage",
        "questions_not_applicable", "average_adjusted_max_points",
        "average_excluded_max_points", "average_normalized_percentage",
        "applicability_status", "applicability_evidence",
    }

    @classmethod
    def setUpClass(cls):
        cls.output_keys = set()
        for name in ("rubric20_semantic_schema.json", "rubric20_output_format.json"):
            path = REPO / "src" / "download" / "prompts" / name
            if path.exists():
                cls.output_keys |= _json_keys(json.loads(path.read_text()))

    def test_every_field_named_anywhere_in_an_agent_resolves(self):
        for agent, path in AGENTS.items():
            text = path.read_text(encoding="utf-8")
            tokens = set(re.findall(
                r"`([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)`", text))
            ignore = self.output_keys | self.ARTIFACTS | self.UNDECLARED_OUTPUT_KEYS
            for token in sorted(tokens - ignore):
                with self.subTest(agent=agent, token=token):
                    self.assertTrue(
                        resolves(token),
                        f"`{token}` is named in {agent} but cannot be reached "
                        "from Dataset")


@unittest.skipUnless(HYBRID.exists(), "hybrid scorer not present")
class TestTheUnreachableQuestions(unittest.TestCase):
    """Q5 and Q10 scored the same value on all 25 current records.

    Resolution alone does not catch these: Q10's fields resolved and it still
    scored 0 every time, because `str(has_formats)` searched the text of a
    boolean. So these assert the scores, on records shaped like the real ones.
    """

    @classmethod
    def setUpClass(cls):
        cls.module = _hybrid()

    def _score(self, data, q):
        return self.module.evaluate_question(data, q)[0]

    def test_standard_formats_and_a_schema_reach_the_top_band(self):
        """Q10. `formats_str = str(has_formats)` is `"True"`, and no format
        name is a substring of that — 5 points were unreachable."""
        self.assertEqual(self._score(
            {"distribution_formats": [{"name": "Parquet"}, {"name": "TSV"}],
             "conforms_to": "https://w3id.org/linkml/d4d"}, 10), 5)

    def test_standard_formats_without_a_schema_reach_the_middle_band(self):
        self.assertEqual(self._score(
            {"distribution_formats": [{"name": "Parquet"}]}, 10), 3)

    def test_no_recognisable_format_still_scores_zero(self):
        """The complement — the fix must not make the question unfailable."""
        self.assertEqual(self._score(
            {"distribution_formats": [{"name": "bespoke binary blob"}]}, 10), 0)

    def test_a_recorded_size_passes_the_file_size_question(self):
        """Q5 read `data_characteristics`, which has never been a slot."""
        self.assertEqual(self._score({"total_size_bytes": 4096000000}, 5), 0)
        self.assertEqual(self._score(
            {"file_collections": [{"total_bytes": "12 GB"}]}, 5), 1)

    def test_no_size_anywhere_still_fails(self):
        self.assertEqual(self._score({"instances": [{"name": "participant"}]}, 5), 0)


if __name__ == "__main__":
    unittest.main()
