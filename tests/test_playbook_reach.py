"""A record says whether its runtime read the playbooks (#545).

The four uniform decision rules reach the API path only because each condition
*prompt* carries its own copy of them. The two added to the playbook since —
American English (#502) and the CURIE rule — reach it not at all, which is how
the v4 arm came to carry 135 British spellings.

Playbooks are hashed for every run deliberately: an unchanged hash on an API
record is how you can tell it did not read them. But that inference requires
already knowing the API path skips them, and the obvious reading of "three
files with hashes" is that the run followed them. So the record now says which
case it is.
"""

import re
import unittest
from pathlib import Path

from data_sheets_schema.provenance import (AGENT_PLAYBOOKS, playbook_facts,
                                           runtime_reads_playbooks)

ROOT = Path(__file__).resolve().parents[1]
#: The rules live in one file since #563; before that they were inside
#: d4d-full-core.md, where /d4d-agent could not see them.
PLAYBOOK = ROOT / ".claude/commands/d4d-uniform-rules.md"
PROMPTS = ROOT / "src/download/prompts"


class TestRuntimeClassification(unittest.TestCase):
    def test_the_agentic_runtime_reads_them(self):
        self.assertTrue(runtime_reads_playbooks("Claude Code"))

    def test_the_api_runtime_does_not(self):
        self.assertFalse(runtime_reads_playbooks("Claude API (direct)"))

    def test_an_unstated_runtime_is_neither(self):
        """None is a third case. Recording False for a run that never said
        what it was would assert something nobody established."""
        self.assertIsNone(runtime_reads_playbooks(None))
        self.assertIsNone(runtime_reads_playbooks(""))


class TestTheRecordSaysWhich(unittest.TestCase):
    def test_a_consuming_run_records_it(self):
        block = playbook_facts(consumed=True)
        self.assertIs(block["consumed"], True)
        self.assertIn("opens these files itself", block["consumed_basis"])

    def test_a_non_consuming_run_records_it_and_why_they_are_hashed(self):
        """Otherwise the block reads as an unexplained inconsistency: files
        hashed but not read, with nothing saying that is deliberate."""
        block = playbook_facts(consumed=False)
        self.assertIs(block["consumed"], False)
        self.assertIn("not read", block["consumed_basis"])

    def test_an_unstated_runtime_omits_the_claim(self):
        """Silence rather than a guess — the field is absent, not False."""
        self.assertNotIn("consumed", playbook_facts())

    def test_the_files_are_hashed_either_way(self):
        """The hashes are the evidence; `consumed` only interprets them."""
        for flag in (True, False, None):
            with self.subTest(consumed=flag):
                block = playbook_facts(consumed=flag)
                self.assertEqual(len(block["files"]), len(AGENT_PLAYBOOKS))


class TestTheRuleSetsDoNotSilentlyDiverge(unittest.TestCase):
    """The duplication that caused this.

    One list of decision rules, kept by hand in the playbook and in every
    condition prompt. That is the pattern #518 and #521 kept finding in the
    build, and it diverged the moment two rules were added to one copy only
    (#545).

    Until v5 the copies were byte-identical, so a text-prefix probe could check
    correspondence. They no longer can be: the playbook cites issue numbers and
    real identifiers, and the generic prompt may contain neither — a first draft
    of the v5 block used a real dataset DOI as an example and
    `test_no_dataset_identifiers` refused it, correctly.

    So the correspondence is **declared** below rather than inferred from the
    text. That is weaker than byte-identity and it is the honest weaker thing:
    a table someone must edit beats a probe that silently stops matching.
    """

    #: rule → (a phrase only that rule has in the playbook,
    #:         a phrase only that rule has in the current condition prompt)
    SHARED_RULES = {
        "prefer omission":
            ("prefer omission", "prefer omission"),
        "sources that disagree":
            ("sources that disagree", "sources that disagree"),
        "one referent":
            ("admits one referent", "admits one referent"),
        "no target count":
            ("no target slot count", "no target slot count"),
        # Probed on "write the CURIE", not "as a CURIE": #591 restored the
        # rule's force and the old phrase went with the old framing. A probe
        # pinned to wording rather than substance breaks on every rewrite.
        "curie form":
            ("write the CURIE", "write the CURIE"),
        "identifier provenance":
            ("comes from the evidence", "take it from the evidence"),
        "minted fragment":
            ("does not identify a person", "does not identify a person"),
        "american english":
            ("American English", "American English"),
        "source priority":
            ("ranks higher", "ranks higher"),
        # v6 (#685): the density norm on minting.
        "minting density":
            ("must point at that part", "must point at that part"),
    }

    #: Rules the playbook carries that the condition prompts deliberately do
    #: not, each with the reason. **Empty as of v5**, which is what this guard
    #: was for: American English (#502) and CURIE form were playbook-only
    #: because they were added mid-arm to avoid rotating a pin, and v5 is the
    #: version boundary where they move into the prompt.
    #:
    #: Emptying it does not retire the guard. A rule added to the playbook
    #: tomorrow, mid-arm, for the same good reason, belongs here again — with
    #: its reason, so the divergence is a decision rather than a discovery.
    PLAYBOOK_ONLY: dict[str, str] = {
        "canonical gc label": (
            "Reaches the API path through the manifest-rendered DECLARED "
            "NAMING block (`api_runner.naming_block`, #668), not through "
            "prompt text — the label lives in the manifest so no prompt ever "
            "hardcodes a project alias (#647), and v5 is a closed condition "
            "whose file is not edited after its runs. At the next version "
            "boundary the rule sentence belongs in the prompt body like the "
            "source-priority rule, with the data still rendered. "
            "`test_the_naming_rule_reaches_the_api_path` guards the render."),
    }

    CURRENT_PROMPT = "d4d_generic_arm_prompt_v6.md"

    def test_the_naming_rule_reaches_the_api_path(self):
        """The render is the API path's copy of the rule; guard its substance.

        PLAYBOOK_ONLY above says the naming rule reaches the API arm through
        `naming_block` rather than prompt text. That claim is only true while
        the block exists, carries the rule and its carve-outs, and renders for
        every project the manifest declares — so this asserts all three, the
        same both-runtimes-one-condition discipline as the rest of this file.
        """
        from data_sheets_schema.api_runner import naming_block
        from data_sheets_schema.grounding import declared_naming
        naming = declared_naming()
        if not naming:
            self.skipTest("no naming declarations in this checkout")
        for project, declared in naming.items():
            with self.subTest(project=project):
                block = naming_block(project)
                self.assertIsNotNone(block)
                self.assertIn(declared["canonical_label"], block)
                self.assertIn("keep their form exactly", block)
        self.assertIsNone(naming_block("NOT_A_DECLARED_PROJECT"))
        self.assertIsNone(
            naming_block("VOICE", "# Source manifest: not used (crate arm)"),
            "an arm that declares the manifest unused must not receive a "
            "block rendered from it (#603)")

    def _texts(self):
        playbook = PLAYBOOK.read_text(encoding="utf-8")
        prompt = (PROMPTS / self.CURRENT_PROMPT).read_text(encoding="utf-8")
        return (re.sub(r"[*`\s]+", " ", playbook).lower(),
                re.sub(r"[*`\s]+", " ", prompt).lower())

    def test_every_shared_rule_reaches_both(self):
        playbook, prompt = self._texts()
        missing = []
        for name, (in_book, in_prompt) in self.SHARED_RULES.items():
            if in_book.lower() not in playbook:
                missing.append(f"{name}: absent from the playbook")
            if in_prompt.lower() not in prompt:
                missing.append(f"{name}: absent from {self.CURRENT_PROMPT}")
        self.assertEqual(missing, [])

    def test_the_playbook_has_no_rule_this_table_does_not_know(self):
        """A rule added to the playbook and to no prompt is the original defect.

        Counting bullets rather than matching their text: the count is what
        catches an addition, and the table above is what says where it reaches.
        """
        text = PLAYBOOK.read_text(encoding="utf-8")
        # The whole file below its heading, since #563 made the rules a file.
        block = text[text.index("# Uniform decision rules"):]
        bullets = re.findall(r"^- (.+?)(?=\n- |\n\n)", block, re.S | re.M)
        self.assertEqual(
            len(bullets), len(self.SHARED_RULES) + len(self.PLAYBOOK_ONLY),
            "a uniform decision rule was added or removed; say in SHARED_RULES "
            "or PLAYBOOK_ONLY where it reaches")

    def test_the_declared_playbook_only_rules_really_are_absent(self):
        """A stale entry asserts a gap that has closed."""
        _playbook, prompt = self._texts()
        for key in self.PLAYBOOK_ONLY:
            with self.subTest(rule=key):
                self.assertNotIn(key.lower(), prompt)

    def test_the_two_rules_v5_was_for_actually_reached_it(self):
        """PLAYBOOK_ONLY is empty; this is what makes that mean something.

        An empty declaration is satisfied both by "the gap closed" and by
        "someone deleted the entries". This asserts the first.
        """
        block = (PROMPTS / self.CURRENT_PROMPT).read_text(encoding="utf-8")
        block = block.split("--- ADDED IN v5 ---", 1)[1].split(
            "--- END ADDED IN v5 ---", 1)[0]
        self.assertIn("American English", block)
        self.assertIn("CURIE", block)

    def test_every_hashed_playbook_reaches_the_rules(self):
        """The blind spot #563 was filed for.

        This guard only ever opened `d4d-full-core.md`. The rules lived there
        and nowhere else, so `/d4d-agent` — a standalone entry point producing
        full records — ran under none of them, and the file that could silently
        diverge was the one nothing checked.

        Now every playbook a record hashes must either state the rules or name
        the file that does. Reading `AGENT_PLAYBOOKS` rather than a list here,
        so a fifth playbook arrives already covered.
        """
        from data_sheets_schema.provenance import AGENT_PLAYBOOKS
        rules_file = PLAYBOOK.name
        missing = []
        for rel in AGENT_PLAYBOOKS:
            path = ROOT / rel
            if path.name == rules_file:
                continue
            text = path.read_text(encoding="utf-8")
            if rules_file not in text:
                missing.append(str(rel))
        self.assertEqual(missing, [],
                         "a hashed playbook neither states the uniform rules "
                         f"nor points at {rules_file}")

    def test_the_rules_are_not_restated_anywhere_else(self):
        """One copy, or the extraction bought nothing.

        A pointer that sits beside a stale duplicate is worse than either alone:
        two sources of truth and no signal about which is current.
        """
        from data_sheets_schema.provenance import AGENT_PLAYBOOKS
        probe = "no target slot count"
        holders = [str(rel) for rel in AGENT_PLAYBOOKS
                   if probe in (ROOT / rel).read_text(encoding="utf-8")]
        self.assertEqual(holders, [str(p) for p in AGENT_PLAYBOOKS
                                   if p.name == PLAYBOOK.name])

    #: Claims that must hold in *both* texts, phrased as a probe that should
    #: match and a probe that must not. Co-occurrence of a topic is not
    #: agreement about it (#573): both files said "as a CURIE" while one told
    #: the model to write a URL where no prefix is declared and the other said
    #: never to write one.
    AGREEMENTS = (
        # "declared range is `uri`" joined this list when #644 showed the
        # older phrasing — "declared range is a URL" — was itself the defect:
        # a range literally named `uriorcurie` satisfies "is a URL" on a plain
        # reading, and the canary's own report said so in as many words ("the
        # resolver URL for the uriorcurie-ranged id"). The exemption must name
        # the range it means. This test used to *require* the ambiguous
        # phrase, which is a check enforcing the bug.
        # Phrases below are matched against `_texts()` output, which strips
        # backticks and asterisks — so they are written without them. The
        # required phrase names the exemption's range with its boundary
        # spelled out ("uri — not uriorcurie"), because a bare "range is uri"
        # would substring-match "range is uriorcurie" and assert nothing.
        #
        # The ambiguous sentence is *forbidden*, in both texts. The first fix
        # kept "declared range is a url" as an accepted alternative because
        # the playbook still used it — which meant reintroducing the exact
        # #644 sentence into the prompt passed every test, and the claim that
        # this had been mutation-tested was true only of a full rule revert.
        # The playbook is now disambiguated too, so nothing needs the old
        # phrase and its reappearance anywhere is a failure.
        ("a URL-ranged slot still takes a URL",
         ("range is uri — not uriorcurie — takes a url",),
         ("declared range is a url takes a url",)),
        ("string-ranged identifier slots follow their own description",
         ("declared range is string",), ()),
        ("prose and citations are left alone",
         ("prose or a citation",), ()),
        ("an undeclared prefix is never invented",
         ("invent a prefix", "invent one"), ()),
        # A *qualified* ban is what the rule needs: "in an identifier slot,
        # never write a resolver URL where the schema declares a prefix". What
        # is forbidden is an unscoped one, which #573 removed because
        # `download_url` and `access_urls` are URL-ranged.
        ("no unqualified ban on URLs",
         (), ("never as a URL", "never a URL,")),
        ("the ban that remains is scoped to identifier slots",
         ("identifier slot", "range is an identifier",
          "range is uriorcurie"), ()),
        # The #644 lesson as a standing requirement: both texts must name
        # `uriorcurie` explicitly, because "identifier slot" and "URL-ranged
        # slot" are prose categories the model has to map onto the digest's
        # literal range names — and the one range that contains both words is
        # exactly where that mapping inverted. The v5 canary wrote 29/29 ids
        # as resolver URLs under a rule written to forbid them, where v4 with
        # no rule at all wrote 62/68 as CURIEs.
        ("the governed range is named, not paraphrased",
         ("uriorcurie",), ()),
    )

    def test_the_two_texts_do_not_contradict_each_other(self):
        """The check that would have caught #573.

        The parity table above asks whether a rule *reaches* both runtimes. It
        cannot see two rules that both arrive and disagree — and that is what
        shipped: the prompt said an identifier is "never as a URL" with no
        scope, while the playbook said a URL is correct where no prefix is
        declared and that URL-ranged slots and prose are exempt.

        `download_url` and `access_urls` are declared `uri`, so the unscoped
        version told the API arm to put a CURIE where the schema requires a URL.
        """
        playbook, prompt = self._texts()
        problems = []
        for name, required, forbidden in self.AGREEMENTS:
            for text, where in ((playbook, "playbook"), (prompt, "prompt")):
                if required and not any(r.lower() in text for r in required):
                    problems.append(f"{where} does not say: {name}")
                for f in forbidden:
                    if f.lower() in text:
                        problems.append(f"{where} still says {f!r}: {name}")
        self.assertEqual(problems, [])

    def test_the_new_v5_rules_reached_the_playbook_too(self):
        """The mirror direction, which nothing checked before.

        This guard was built for rules that reach the agentic path and not the
        API path. Two of v5's four arrived the other way round — written for the
        prompt, out of #547 and #531 — and a rule the API arm follows while the
        agentic arm does not is the same defect wearing the other shoe.
        """
        playbook, _prompt = self._texts()
        for probe in ("comes from the evidence", "does not identify a person"):
            with self.subTest(probe=probe):
                self.assertIn(probe, playbook)
