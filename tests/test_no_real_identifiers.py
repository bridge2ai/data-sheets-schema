"""No real-world identifier sits in a generic prompt or playbook (#647).

Why this exists: a fix for #644 put `doi:10.60775/…` — AI-READI's DOI prefix
— into the generic prompt, and `test_no_expected_quantities` caught it. The
same edit put `ROR:01an7q238`, **UC Berkeley's real ROR id**, into text sent
verbatim to the model, and nothing caught it: its digits are flanked by
letters so the quantity regex misses it, and the per-version
`test_no_dataset_identifiers` scans only each version's *added block* with a
fixed token list. It had sat in the playbook and a schema comment for weeks.

An example identifier in a prompt is a candidate for verbatim copy-through
into a generated record, where it grounds against nothing — and a real one
belonging to an unrelated institution is a false claim waiting to happen.

So this scans **whole files**, every generic prompt and both playbooks, for
the *shape* of a real identifier rather than a list of known tokens. Exact
matches that are known and cannot be removed are allowlisted with the reason;
the allowlist is checked in both directions, so it cannot rot.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: What a real identifier looks like. Form-only phrasing in the rules — "a
#: ROR: CURIE, not the ror.org URL" — contains none of these by construction.
SHAPES = {
    "ROR CURIE": re.compile(r"\bROR:[0-9a-z]{9}\b"),
    "ror.org URL": re.compile(r"ror\.org/[0-9a-z]{9}\b"),
    "DOI prefix": re.compile(r"\b10\.\d{4,}/\S+"),
    "doi: CURIE": re.compile(r"\bdoi:10\.\d{4,}"),
    "orcid.org URL": re.compile(r"orcid\.org/\d"),
    "bare ORCID": re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b"),
    "PMID": re.compile(r"\bPMID:?\s?\d{5,}\b"),
    "PMCID": re.compile(r"\bPMC\d{5,}\b"),
}

#: Every text sent to the model, or driving an agent, under a generic
#: condition. Both playbooks are included because #647's ROR sat in one.
TEXTS = sorted(REPO.glob("src/download/prompts/d4d_generic_arm_prompt*.md")) + [
    REPO / ".claude" / "commands" / "d4d-uniform-rules.md",
    REPO / ".claude" / "commands" / "d4d-full-core.md",
]

#: Known real identifiers that cannot be removed, each with why. A file that
#: is pinned and has already been sent is a condition that exists; editing it
#: would rotate its pin and re-baseline every run made under it.
ALLOWED = {
    ("src/download/prompts/d4d_generic_arm_prompt_v5.md", "ror.org/032db5x82"):
        "the v5 prompt's own rationale for the identifier rule cites the "
        "University of South Florida's ROR as the example of an identifier a "
        "run supplied from memory (#547). The prompt is pinned "
        "(canonical_hashes.yaml) and 42 runs hashed it; editing it would "
        "re-baseline a condition that already exists. The example is inside "
        "prose explaining why *not* to do this, and no generated record has "
        "been found carrying it.",
}


def real_identifiers(text: str) -> list[tuple[str, str]]:
    """Every (shape, token) in `text` that looks like a real identifier."""
    hits = []
    for shape, rx in SHAPES.items():
        for m in rx.finditer(text):
            hits.append((shape, m.group(0)))
    return hits


class TestTheScannerSeesEachShape(unittest.TestCase):
    """The scanner itself, on strings — so a regression in a pattern fails
    here rather than being hidden by a clean corpus."""

    def test_each_shape_is_found(self):
        samples = {
            "ROR CURIE": "cite ROR:01an7q238 here",
            "ror.org URL": "see https://ror.org/01an7q238 for it",
            "DOI prefix": "under 10.60775/fairhub.1 as released",
            "doi: CURIE": "the id doi:10.13026/abcd-ef12",
            "orcid.org URL": "https://orcid.org/0000-0002-1825-0097",
            "bare ORCID": "ORCID 0000-0002-1825-0097 given",
            "PMID": "PMID: 12345678 and PMID:87654321",
            "PMCID": "PMC1234567",
        }
        for shape, text in samples.items():
            with self.subTest(shape=shape):
                self.assertTrue(any(s == shape for s, _ in real_identifiers(text)))

    def test_form_only_phrasing_is_clean(self):
        """The wording the rules actually use contains none of the shapes."""
        clean = ("Give a ROR: CURIE, not the ror.org URL. Cite a DOI as doi:<prefix>/"
                 "<suffix>. An ORCID is a CURIE of the form orcid:XXXX-XXXX-XXXX-XXXX. "
                 "Do not invent a PMID.")
        self.assertEqual(real_identifiers(clean), [])


class TestNoRealIdentifierInAnyPromptOrPlaybook(unittest.TestCase):
    def test_every_text_exists(self):
        for p in TEXTS:
            with self.subTest(path=str(p.relative_to(REPO))):
                self.assertTrue(p.exists())

    def test_no_unlisted_real_identifier(self):
        offenders = []
        for p in TEXTS:
            rel = str(p.relative_to(REPO))
            for shape, tok in real_identifiers(p.read_text(encoding="utf-8")):
                if (rel, tok) not in ALLOWED:
                    offenders.append(f"{rel}: {shape} {tok!r}")
        self.assertEqual(offenders, [],
                         "a real identifier in text sent to the model is a candidate "
                         "for copy-through into a record where it grounds against "
                         "nothing (#647). Remove it, or if it cannot be removed, "
                         "allowlist it with the reason.\n" + "\n".join(offenders))

    def test_every_allowlisted_identifier_is_still_there(self):
        """An allowlist entry for a token that is gone is a claim that has
        stopped being true; it comes out when the token does."""
        for (rel, tok), why in ALLOWED.items():
            with self.subTest(entry=f"{rel}: {tok}"):
                self.assertTrue(why.strip(), "an allowlist entry needs a reason")
                self.assertIn(tok, (REPO / rel).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
