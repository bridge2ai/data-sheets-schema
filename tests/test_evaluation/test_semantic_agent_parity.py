"""The rubric20 agents must score the rubric the repository publishes (#314).

`rubric20-semantic` scored five questions the rubric does not define, and the
conversational `rubric20` agent scored six. Most were the rubric broadening
scope while the agents kept the narrower wording; one was not a rename at all —
both agents scored a retired "Interlinking Across Platforms" while the rubric's
Q20 is "Bias Documentation and Responsible AI Alignment", so the responsible-AI
question was **not scored by either agent at all**.

That also explains the denominator. Both treated Q20 as pass/fail worth 1 point
where the rubric defines it numeric worth 5, which is exactly the 84 against 88.

#275 corrected the denominator in the constants, the summariser scripts and the
API judge's system prompt, and its tests assert against those. Nothing compared
the *agents* to `data/rubric/rubric20.txt`, which is why they kept both the old
total and the old questions. This is that comparison.

`rubric20_system_prompt.md` is deliberately absent from `AGENTS`: it interpolates
`{RUBRIC_SPECIFICATION}` from the rubric file at run time, so its questions
cannot drift. It is the shape the agents do not have.

A note on the denominator assertions. The obvious form — `assertNotIn("84", …)`
— cannot be used: it fires on `4,184 participants` and on a UUID, and would have
had to be deleted the first time someone wrote a plausible number. These match
the maximum where it is *stated*, which is where a stale value does harm.
"""

import json
import re
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.constants.evaluation import RUBRIC20_PATH

REPO = Path(__file__).resolve().parents[2]
AGENTS = {
    "rubric20": REPO / ".claude" / "agents" / "d4d-rubric20.md",
    "rubric20-semantic": REPO / ".claude" / "agents" / "d4d-rubric20-semantic.md",
}
SCHEMA = REPO / "src" / "download" / "prompts" / "rubric20_semantic_schema.json"
OUTPUT_FORMAT = REPO / "src" / "download" / "prompts" / "rubric20_output_format.json"
SUMMARY_SCHEMA = (REPO / "src" / "data_sheets_schema" / "schema"
                  / "D4D_Evaluation_Summary.yaml")

#: Where a maximum is *asserted* rather than merely occurring as a digit.
#:
#: `[:*\s]+` rather than `[:\s]+`: the headline site is written
#: `**Maximum Possible Score:** 88 points`, and a separator class that does not
#: admit the bold markers skips the one place a reader looks first. A mutation
#: check caught exactly that — reverting it to 84 left every test green.
STATED_MAXIMUM = re.compile(
    r"""(?:maximum(?:\s+possible)?(?:\s+score)?[:*\s]+|"max_points":\s*|
         "adjusted_max_points":\s*|max_score:\s*|max_points:\s*)(\d+)""",
    re.I | re.X)


def _questions():
    return yaml.safe_load(Path(RUBRIC20_PATH).read_text())[
        "d4d_evaluation_rubric"]["rubric"]


def _max_score(question):
    return 1 if question.get("score_type") == "pass_fail" else 5


def _maximum():
    return sum(_max_score(q) for q in _questions())


class TestQuestionParity(unittest.TestCase):
    """Names and score types, per agent, against `rubric20.txt`."""

    @classmethod
    def setUpClass(cls):
        cls.canon = _questions()
        cls.text = {}
        cls.headings = {}
        for name, path in AGENTS.items():
            text = path.read_text(encoding="utf-8")
            cls.text[name] = text
            cls.headings[name] = {
                int(n): title.strip() for n, title in
                re.findall(r"^#### Question (\d+): (.+)$", text, re.M)}

    def test_every_agent_definition_exists(self):
        for name, path in AGENTS.items():
            with self.subTest(agent=name):
                self.assertTrue(path.exists(), f"{path} is missing")

    def test_each_agent_defines_every_question_the_rubric_does(self):
        for name in AGENTS:
            with self.subTest(agent=name):
                self.assertEqual(sorted(self.headings[name]),
                                 list(range(1, len(self.canon) + 1)))

    def test_every_question_name_matches(self):
        """Names, not just numbers.

        Most of the drifted questions kept a narrower older name while the
        rubric broadened the scope, which is invisible if only the count is
        checked.
        """
        for name in AGENTS:
            for i, q in enumerate(self.canon, 1):
                with self.subTest(agent=name, question=i):
                    self.assertEqual(self.headings[name][i].lower(),
                                     (q.get("name") or "").strip().lower())

    def test_the_retired_question_is_gone(self):
        """`Interlinking Across Platforms` was Q20 and is no longer in the rubric."""
        for name, text in self.text.items():
            with self.subTest(agent=name):
                self.assertNotIn("Interlinking Across Platforms", text)

    def test_the_responsible_ai_question_is_scored(self):
        """The one both agents were silently omitting."""
        for name, text in self.text.items():
            with self.subTest(agent=name):
                self.assertIn("Bias Documentation and Responsible AI Alignment",
                              text)

    def test_score_types_match(self):
        """A pass/fail question worth 1 where the rubric says numeric worth 5
        is where the 84-against-88 came from."""
        for name, text in self.text.items():
            for i, q in enumerate(self.canon, 1):
                declared = "pass/fail" if q.get("score_type") == "pass_fail" \
                    else "numeric 0-5"
                block = text.split(f"#### Question {i}: ", 1)[1].split("---", 1)[0]
                with self.subTest(agent=name, question=i):
                    self.assertIn(f"**Scoring ({declared}):**", block)


class TestDenominatorParity(unittest.TestCase):
    """Every place a maximum is stated must agree with the questions."""

    def test_the_computed_maximum_is_what_the_questions_define(self):
        self.assertEqual(_maximum(), 88)

    def test_no_agent_states_a_maximum_other_than_the_computed_one(self):
        """Matches where a maximum is asserted, so an incidental `84` inside a
        participant count or a UUID cannot mask or fake a failure."""
        for name, path in AGENTS.items():
            for stated in STATED_MAXIMUM.findall(path.read_text(encoding="utf-8")):
                with self.subTest(agent=name, stated=stated):
                    self.assertNotEqual(int(stated), 84,
                                        "the superseded 84-point maximum")

    def test_each_agent_states_the_computed_maximum(self):
        for name, path in AGENTS.items():
            stated = {int(n) for n in
                      STATED_MAXIMUM.findall(path.read_text(encoding="utf-8"))}
            with self.subTest(agent=name):
                self.assertIn(_maximum(), stated)

    def test_the_per_category_maxima_sum_to_the_total(self):
        """The 84 survived a header-only fix once already.

        Each agent decomposes the maximum by category; a judge shown category
        maxima that sum to 84 will reproduce 84 whatever the header says.
        """
        line = re.compile(r"^- \*\*.+?\(Q(\d+)-(\d+)\):\*\* (\d+) points max", re.M)
        canon = _questions()
        for name, path in AGENTS.items():
            found = line.findall(path.read_text(encoding="utf-8"))
            with self.subTest(agent=name):
                self.assertTrue(found, "no per-category decomposition found")
                self.assertEqual(sum(int(m[2]) for m in found), _maximum())
                for first, last, stated in found:
                    want = sum(_max_score(q)
                               for q in canon[int(first) - 1:int(last)])
                    with self.subTest(category=f"Q{first}-{last}"):
                        self.assertEqual(int(stated), want)

    @unittest.skipUnless(SCHEMA.exists(), "semantic schema not present")
    def test_the_schema_const_does_not_reject_a_correct_score(self):
        """It is a `const`, so a stale value does not merely mislead — it
        rejects any evaluation reporting the right maximum."""
        node = json.loads(SCHEMA.read_text())["properties"]["overall_score"] \
            ["properties"]["max_points"]
        self.assertEqual(node.get("const"), _maximum())

    @unittest.skipUnless(SUMMARY_SCHEMA.exists(), "summary schema not present")
    def test_the_evaluation_summary_schema_agrees(self):
        for line in SUMMARY_SCHEMA.read_text().splitlines():
            if "rubric20" in line.lower():
                with self.subTest(line=line.strip()[:60]):
                    self.assertNotIn("84", line)


@unittest.skipUnless(OUTPUT_FORMAT.exists(), "output format not present")
class TestTheWorkedExample(unittest.TestCase):
    """`rubric20_output_format.json` is a filled-in evaluation.

    No code reads it, which is exactly why it rotted: it demonstrated the
    retired Q20 as pass/fail. An example that contradicts the specification is
    the version a model will copy.
    """

    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(OUTPUT_FORMAT.read_text())
        cls.canon = _questions()
        cls.by_id = {q["id"]: q for c in cls.doc["categories"]
                     for q in c["questions"] if isinstance(q, dict)}

    def test_the_example_scores_the_rubrics_questions(self):
        for i, q in enumerate(self.canon, 1):
            with self.subTest(question=i):
                self.assertIn(i, self.by_id)
                self.assertEqual(self.by_id[i]["name"].lower(),
                                 q["name"].strip().lower())
                self.assertEqual(self.by_id[i]["score_type"],
                                 q.get("score_type"))
                self.assertEqual(self.by_id[i]["max_score"], _max_score(q))

    def test_the_examples_arithmetic_holds(self):
        total = 0
        for c in self.doc["categories"]:
            qs = [q for q in c["questions"] if isinstance(q, dict)]
            with self.subTest(category=c["name"]):
                self.assertEqual(c["category_score"],
                                 sum(q["score"] for q in qs))
                self.assertEqual(c["category_max"],
                                 sum(q["max_score"] for q in qs))
            total += c["category_score"]
        overall = self.doc["overall_score"]
        self.assertEqual(overall["total_points"], total)
        self.assertEqual(overall["max_points"], _maximum())
        self.assertAlmostEqual(overall["percentage"],
                               round(total / _maximum() * 100, 1), places=1)


if __name__ == "__main__":
    unittest.main()
