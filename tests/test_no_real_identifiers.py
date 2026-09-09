"""No real-world identifier sits in text the model is sent, or in the text
the next prompt is drafted from (#647).

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

What is scanned, and why each (#1107 review). The **prompt body** of every
generic prompt is sent verbatim; it is the fatal surface. The **rationale**
above `## Prompt body` is never sent — `prompt_body` strips it — but the
next version is drafted from it, which is how the v5 rationale's real ROR
would have travelled; it is scanned too. The two **playbooks** drive the
agentic runtime. The **rendered schema digest** (`Dataset`, `CoreDataset`)
is sent ahead of the arm prompt on every API request (`ASSEMBLY_LAYOUT`),
so a slot description is as model-facing as a rule — that is where the last
real identifier in the scanned surface sat until #1114 removed it.

The allowlist is checked in both directions and each entry is held to the
line it claims to be on; an entry cannot outlive its token, and a token
cannot move into a prompt body under an entry written for its rationale.
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
    "DOI prefix": re.compile(r"\b10\.\d{3,9}/\S+"),            # registrants of 3+ digits (review note 6)
    "doi: CURIE": re.compile(r"\bdoi:10\.\d{3,9}"),
    "orcid.org URL": re.compile(r"orcid\.org/\d"),
    "bare ORCID": re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b"),
    "PMID": re.compile(r"\bPMID:?\s?\d{5,}\b"),
    "PMCID": re.compile(r"\bPMC\d{5,}\b"),
    "clinical trial": re.compile(r"\bNCT\d{8}\b"),
    "RRID": re.compile(r"\bRRID:\s?[A-Z]+_?\w+"),
    "dbGaP": re.compile(r"\bphs\d{6}\b"),
}


def _prompt_texts() -> list[tuple[str, str, str]]:
    """(name, surface, text) for each generic prompt: the body the model is
    sent, and the rationale it is drafted from, as separate surfaces."""
    out = []
    for p in sorted(REPO.glob("src/download/prompts/d4d_generic_arm_prompt*.md")):
        rel = str(p.relative_to(REPO))
        whole = p.read_text(encoding="utf-8")
        head, sep, body = whole.partition("## Prompt body")
        out.append((rel, "body", body if sep else whole))
        if sep:
            out.append((rel, "rationale", head))
    return out


def _digest_texts() -> list[tuple[str, str, str]]:
    """Anchored to this checkout, like every other surface: `digest_text`'s
    default schema path is cwd-relative (`resolve_schema`, #659), so a test
    run with the cwd at another checkout would scan that checkout's schema
    and pass for the wrong tree (#1107 review, round 2)."""
    from data_sheets_schema import schema_digest
    return [(f"schema digest ({cls})", "digest",
             schema_digest.digest_text(cls, REPO / str(schema_digest.CLASS_SCHEMA[cls])))
            for cls in ("Dataset", "CoreDataset")]


def texts() -> list[tuple[str, str, str]]:
    """Every scanned surface: (name, surface, text)."""
    return (_prompt_texts()
            + [(str(p.relative_to(REPO)), "playbook", p.read_text(encoding="utf-8"))
               for p in (REPO / ".claude" / "commands" / "d4d-uniform-rules.md",
                         REPO / ".claude" / "commands" / "d4d-full-core.md")]
            + _digest_texts())


#: Known real identifiers that cannot yet be removed: (name, token) ->
#: {reason, surface, line_contains}. `surface` is the only surface the token
#: may sit on and `line_contains` a phrase the token's line must carry, so
#: the entry holds the token to the context that justifies it.
ALLOWED: dict[tuple[str, str], dict[str, str]] = {
    # Empty since #1114 removed the doi description's real Nature DOI. An
    # entry, when one is needed again, is {surface, line_contains, reason}.
}


def allowlist_findings(allowed: dict, surfaces: list[tuple[str, str, str]]) -> list[str]:
    """Both directions of the allowlist, as strings a test can assert on:
    a scanned token not allowlisted; an entry whose token is gone; an entry
    whose token has left the line that justified it. Factored out so the
    machinery is exercised even while the real allowlist is empty (#1126
    review, S5)."""
    out = []
    by_name = {(n, s): t for n, s, t in surfaces}
    for name, surface, text in surfaces:
        for shape, tok in real_identifiers(text):
            if (name, tok) not in allowed:
                out.append(f"unlisted: {name} [{surface}] {shape} {tok!r}")
    for (name, tok), entry in allowed.items():
        text = by_name.get((name, entry["surface"]))
        if text is None:
            out.append(f"no surface: {name} [{entry['surface']}]"); continue
        lines = [ln for ln in text.splitlines() if tok in ln]
        if not lines:
            out.append(f"gone: {name} {tok!r}"); continue
        for ln in lines:
            if entry["line_contains"] not in ln:
                out.append(f"moved: {name} {tok!r} off a line containing {entry['line_contains']!r}")
    return out


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
            "DOI prefix": "under 10.60775/fairhub.1 as released, or 10.123/x",
            "doi: CURIE": "the id doi:10.13026/abcd-ef12",
            "orcid.org URL": "https://orcid.org/0000-0002-1825-0097",
            "bare ORCID": "ORCID 0000-0002-1825-0097 given",
            "PMID": "PMID: 12345678 and PMID:87654321",
            "PMCID": "PMC1234567",
            "clinical trial": "registered as NCT01234567",
            "RRID": "RRID:SCR_001234 and RRID: AB_2315147",
            "dbGaP": "accession phs001234",
        }
        for shape, text in samples.items():
            with self.subTest(shape=shape):
                self.assertTrue(any(s == shape for s, _ in real_identifiers(text)))

    def test_form_only_phrasing_is_clean(self):
        """The wording the rules actually use contains none of the shapes."""
        clean = ("Give a ROR: CURIE, not the ror.org URL. Cite a DOI as doi:<prefix>/"
                 "<suffix> in format 10.xxxx/xxxxx. An ORCID is a CURIE of the form "
                 "orcid:XXXX-XXXX-XXXX-XXXX. Do not invent a PMID, an NCT number or an RRID.")
        self.assertEqual(real_identifiers(clean), [])


class TestTheAllowlistMachinery(unittest.TestCase):
    """The real allowlist is empty since #1114; the checks it relies on are
    driven here over a synthetic one so they cannot rot unexercised."""

    SURFACES = [("t", "digest", "a line with ROR:01an7q238 (e.g. context)\nanother line\n")]

    def test_an_entry_on_its_line_passes(self):
        allowed = {("t", "ROR:01an7q238"): {"surface": "digest", "line_contains": "e.g.", "reason": "x"}}
        self.assertEqual(allowlist_findings(allowed, self.SURFACES), [])

    def test_an_unlisted_token_is_a_finding(self):
        self.assertEqual(allowlist_findings({}, self.SURFACES), ["unlisted: t [digest] ROR CURIE 'ROR:01an7q238'"])

    def test_a_token_that_left_its_line_is_a_finding(self):
        allowed = {("t", "ROR:01an7q238"): {"surface": "digest", "line_contains": "nowhere", "reason": "x"}}
        self.assertEqual([f.split(":")[0] for f in allowlist_findings(allowed, self.SURFACES)], ["moved"])

    def test_an_entry_whose_token_is_gone_is_a_finding(self):
        allowed = {("t", "ROR:09zzzzzzz"): {"surface": "digest", "line_contains": "e.g.", "reason": "x"}}
        found = allowlist_findings(allowed, self.SURFACES)
        self.assertTrue(any(f.startswith("gone:") for f in found), found)


class TestNoRealIdentifierOnAnyModelFacingSurface(unittest.TestCase):
    def test_every_surface_is_present(self):
        names = {(n, s) for n, s, _ in texts()}
        self.assertGreaterEqual(len([1 for n, s in names if s == "body"]), 9)   # v1 + v2–v9; a v10 adds one
        self.assertIn(("schema digest (Dataset)", "digest"), names)
        self.assertIn((".claude/commands/d4d-full-core.md", "playbook"), names)

    def test_no_unlisted_real_identifier(self):
        offenders = []
        for name, surface, text in texts():
            for shape, tok in real_identifiers(text):
                if (name, tok) not in ALLOWED:
                    offenders.append(f"{name} [{surface}]: {shape} {tok!r}")
        self.assertEqual(offenders, [],
                         "a real identifier on a model-facing surface is a candidate "
                         "for copy-through into a record where it grounds against "
                         "nothing, and one in a rationale is copied into the next "
                         "prompt (#647). Remove it, or if it cannot be removed yet, "
                         "allowlist it with the reason and the issue.\n" + "\n".join(offenders))

    def test_no_prompt_body_carries_any_real_identifier_allowlisted_or_not(self):
        """The body is what is sent; nothing is allowlisted there. The first
        version's allowlist was keyed by file, so a token moved from the
        rationale into the body passed under the rationale's entry (#1107
        review, finding 5)."""
        for name, surface, text in texts():
            if surface == "body":
                self.assertEqual(real_identifiers(text), [], name)

    def test_every_allowlisted_identifier_is_still_where_it_says(self):
        """An entry for a token that is gone is a claim that has stopped being
        true; an entry whose token has left the line that justified it is one
        that has stopped applying. Both come out when the token moves."""
        by_name = {(n, s): t for n, s, t in texts()}
        for (name, tok), entry in ALLOWED.items():
            with self.subTest(entry=f"{name}: {tok}"):
                self.assertTrue(entry["reason"].strip(), "an allowlist entry needs a reason")
                text = by_name.get((name, entry["surface"]))
                self.assertIsNotNone(text, f"no surface {entry['surface']!r} named {name!r}")
                lines = [ln for ln in text.splitlines() if tok in ln]
                self.assertTrue(lines, "the token is gone; drop the entry")
                for ln in lines:
                    self.assertIn(entry["line_contains"], ln,
                                  "the token has left the line that justified the entry")

    def test_the_removed_v5_ror_stays_out(self):
        """The first version allowlisted USF's ROR in the v5 rationale as
        unremovable; it was removable (rationale-only, pin rotated, body
        sha unchanged). It must not come back on any surface."""
        for name, surface, text in texts():
            self.assertNotIn("032db5x82", text, f"{name} [{surface}]")


if __name__ == "__main__":
    unittest.main()
