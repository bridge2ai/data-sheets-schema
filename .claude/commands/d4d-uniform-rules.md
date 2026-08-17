# Uniform decision rules (all conditions, all projects, both runtimes)

**This file is the single copy.** It was extracted from
`.claude/commands/d4d-full-core.md` because the rules lived there and nowhere
else, so `/d4d-agent` — a standalone entry point that generates full records —
ran under none of them (#563). That is the same duplication defect as #518,
#521 and #545, one level further out: a list of content maintained by hand in
several places diverges the moment one copy is edited.

Every playbook that generates a record reads this file. The condition prompts
carry the same rules in their own words, because a prompt is sent to a model
that cannot open files; `tests/test_playbook_reach.py` checks that
correspondence in both directions.

Enforce these whether or not a prompt file was used to launch.


These are part of the method rather than tuning, because each applies identically
to every project:

- Populate a slot only where the declared bundle supports it. **Prefer omission
  over inference:** an absent slot is a correct answer when the evidence is
  absent, and a plausible guess is not.
- Where the declared bundle contains sources that disagree, represent what the
  evidence states rather than silently selecting one. Do not merge distinct
  entities into a single claim.

- **Where two sources disagree, prefer the one the manifest ranks higher.**
  State its value, and record in the caveat that the sources disagreed, what
  each said, and which was preferred. The ranking is `source_priority` in
  `data/preprocessed/source_manifest.yaml`, lowest tier strongest;
  `d4d download priority --project X` lists it and
  `d4d download priority --project X --decide a,b` answers a specific pair.

  **Where the disagreeing sources share the same rank the ranking cannot
  decide**: represent what the evidence states, as the rule above says. This
  refines that rule rather than replacing it.

  It exists because a v4 CHORUS record wrote that no instance count was
  asserted "because the two sources give different figures … and the bundle
  offers no basis for preferring one". The rule was right; the basis was
  missing.
- `Dataset` admits one referent. Choose the one the declared bundle best
  supports, state that choice in the reconciliation report, and hold to it
  consistently across both records.
- There is no target slot count, no expected density, and no expected
  relationship to any other arm or project. Apply your own judgment about what
  the evidence supports.
- **In an identifier slot, never write a resolver URL where the schema declares
  a prefix — write the CURIE.** `ROR:01an7q238`, not
  `https://ror.org/01an7q238`; `ORCID:0000-0002-…`, not the orcid.org URL;
  `doi:10.13026/…`, not `https://doi.org/…`. Two records naming one thing in
  one form produce one identity; the same thing written as a prefix here and a
  resolver URL there produces two. A resolver URL in such a slot is a defect
  even though it resolves: the v5 canary wrote 45 of them and that is what
  #591 records.

  **This governs slots whose declared range is an identifier** —
  `uriorcurie`. A slot whose declared range is a URL takes a URL: `download_url`
  and `access_urls` are declared `uri` and a CURIE there is wrong. A URL inside
  prose or a citation is text, not an identifier, and must be left exactly as
  written.

  **Where no declared prefix fits, never invent one.** A prefix the schema does
  not declare resolves to nothing, so do not mint `b2ai-voice:` or similar
  (#531). Hang the identifier off one the evidence supplies — see the fragment
  rule below — and where no fragment is possible either, a resolvable URL is the
  better answer. Check the schema's `prefixes:` block rather than guessing.

- **An identifier is a fact and comes from the evidence.** Take it from the
  declared bundle or omit it; do not supply an identifier you recognise but the
  bundle does not state. A correct identifier the evidence does not contain is
  still an unsupported claim, and to a reader who was not present it is
  indistinguishable from a wrong one. Naming an organisation the bundle names is
  grounded; adding that organisation's ROR from your own knowledge is not — the
  2026-08-13 arm did exactly this, supplying RORs for institutions the bundle
  names only in prose (#547). `grounding.absent` in the provenance record counts
  them.

- **Where something needs an identifier and the bundle supplies none, hang it
  off one the bundle does supply** — a fragment on the identifier of the thing
  it is part of, `doi:10.60775/fairhub.3#split-train`, rather than a new
  namespace (#531). A person is identified by an ORCID and an organisation by a
  ROR; **a fragment appended to an organisation's ROR does not identify a
  person**, it asserts something false about that organisation.

- **Write generated prose in American English** — `program`, `organization`,
  `analyze`, `license`, `center`, `labeling`, `enrollment`. This is house style
  for the text *you* compose, and it applies to identifiers you mint as well as
  to descriptions.

  Three carve-outs, and they are not optional:

  - **Quoted source text keeps its original spelling.** Changing a quotation to
    match house style corrupts evidence, which is the one thing the provenance
    guard exists to prevent. The bundles contain `licence` 13 times and
    `programme` 6.
  - **Proper nouns keep their spelling** — "Wellcome Trust Sanger Centre",
    "Medical Research Council Programme Grant". A name is not prose.
  - **Identifiers copied from a source keep the source's spelling.** An id you
    take from a crate or a DOI is a token, not a sentence. Only ids *you* mint
    follow house style.

The rule about there being no target slot count is the load-bearing one: it is
what makes a slot count an observation rather than a target. Named rather than
referred to by position, so inserting a rule cannot silently point this sentence
at a different one.
