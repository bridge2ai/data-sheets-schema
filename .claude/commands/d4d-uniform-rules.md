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
  a prefix — write the CURIE.** A `ROR:` CURIE, not the ror.org URL; an
  `ORCID:` CURIE, not the orcid.org URL; a `doi:` CURIE, not the doi.org
  resolver form. (Form only, deliberately: an example carrying a real registry
  identifier or a real DOI prefix leaks one project's identity into text every
  project reads — one project's real publisher prefix sat here for a month,
  #647.) Two records naming one thing in one form produce one identity;
  the same thing written as a prefix here and a resolver URL there produces
  two. A resolver URL in such a slot is a defect even though it resolves: the
  v5 canary wrote 45 of them and that is what #591 records.

  **This governs slots whose declared range is an identifier** —
  `uriorcurie`. A slot whose declared range is `uri` — not `uriorcurie` —
  takes a URL: `download_url` and `access_urls` are declared `uri` and a CURIE
  there is wrong. ("Not `uriorcurie`" is load-bearing: the 2026-08-19 canary
  read the older wording, "declared range is a URL", as covering `uriorcurie`
  and expanded every id to a resolver URL — #644.) A slot whose declared range
  is `string` follows its own description and pattern even when it holds an
  identifier — the `doi` slot takes the bare DOI, neither prefixed nor
  resolved. A URL inside prose or a citation is text, not an identifier, and
  must be left exactly as written.

  **Where no declared prefix fits, never invent one.** A prefix the schema does
  not declare resolves to nothing, so do not mint `b2ai-voice:` or similar
  (#531). Hang the identifier off one the evidence supplies — see the fragment
  rule below — and where no fragment is possible either, a resolvable URL is the
  better answer. Check the schema's `prefixes:` block rather than guessing.

- **An identifier that names something outside this dataset is a fact, and comes from the evidence.** Take it from the
  declared bundle or omit it; do not supply an identifier you recognise but the
  bundle does not state. A correct identifier the evidence does not contain is
  still an unsupported claim, and to a reader who was not present it is
  indistinguishable from a wrong one. Naming an organisation the bundle names is
  grounded; adding that organisation's ROR from your own knowledge is not — the
  2026-08-13 arm did exactly this, supplying RORs for institutions the bundle
  names only in prose (#547). `grounding.absent` in the provenance record counts
  them.

- **An identifier for a part of this dataset, existing nowhere outside this
  record, is a label rather than a claim about the world**, so the rule above
  does not reach it: no evidence can supply it. The test is whether the thing
  named has a referent outside this record. Where it does not, hang the label
  off one the bundle does supply — a fragment on the identifier of the thing
  it is part of, `<the dataset's own DOI CURIE>#split-train`, rather than a new
  namespace (#531). A person is identified by an ORCID and an organisation by a
  ROR; **a fragment appended to an organisation's ROR does not identify a
  person**, it asserts something false about that organisation.

- **Within the rule above, mint a fragment only where another value in the
  record must point at that part** (v6, #685) — a split a task names, a
  subset a distribution cites, a collection a file belongs to. A part nothing
  points at is described in prose, not labeled: an identifier no value in the
  record uses is not a label, it is noise that reads as structure. Name the
  same part with the same fragment every time a value points at it, and mint
  nothing for a part that is only described. This is the density norm the
  rule above lacked; the evidence for it is in the v6 analysis plan, not
  here, because this file is read by a generating model.

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

- **Call the project by its declared canonical label** — the manifest's
  `naming:` block (`data/preprocessed/source_manifest.yaml`) declares one
  label per project, taken from the B2AI Standards Explorer (#668). Use it in
  every sentence *you* compose; one project written many ways reads as many
  projects, and the v5 canonical records wrote one project four ways. The
  same three carve-outs as the American-English rule apply unchanged: quoted
  source text, proper nouns as a source states them (a consortium's name in
  the release's own citation is a citation, not your prose), and identifiers
  including URLs keep their form exactly. The B2AI_ORG ids in the manifest
  are provenance of where the mapping came from — never write one into a
  record.

- **A class-ranged attribute the schema digest marks `(reference — a string,
  not an object)` takes exactly that string; every other class-ranged
  attribute takes an object with the keys the digest lists for that class**
  (v8, R1) — a `Grant` under `grants` with its `grant_number`, an
  `Organization` under `affiliations`, a `Person` under
  `principal_investigator` with its `name` and, where the evidence states
  them, `orcid`, `email` and `affiliation`. The scalar-range rule governs
  scalar ranges only; never reduce an object the digest asks for to a
  string, nor inflate a marked reference into an object.

- **Name to yourself what a passage is about and when before writing it as
  the referent's current state** (v8, R2): a plan, proposal or future release
  is stated as such or omitted; an earlier release or archived version is a
  fact about that version; a passage whose subject is another dataset
  describes that other dataset and belongs only in `related_datasets`. A
  receipt's snippet comes from a passage about the value's own subject.

- **A figure the record derives — a sum, difference, fraction, count — is
  stated as the record's own computation with its inputs named, never as a
  figure a source reported** (v8, R3); it is receipted at its own path by
  the passages stating its inputs, since a passage cannot receipt an
  arithmetic result it does not contain. Where a derived figure and a stated
  total disagree, record both and the difference in `source_caveats`.

- **A roster the bundle states entry by entry — creators, funders,
  variables, file collections, files — is receipted entry by entry** (v8,
  R4): each entry carries its own receipt naming the passage that states it;
  a roster receipted by one passage for one entry has receipted one entry.

- **A `Person` object's `id` is the ORCID the evidence states, else a
  fragment minted on this record's own id** (v8, R5, #981): `ORCID:` CURIE
  where the documents list one — look for it before minting — otherwise
  `<record id>#person-<name>`; never a `mailto:` or any other scheme as the
  id, the address goes in `email`.

- **A value in one of the referent's own slots is supported by a passage
  whose subject is the referent** (v9, R6, #913): the declared scope names
  the referent and the datasets declared related but distinct, with the
  slot their facts belong in where it states one; a passage about another
  dataset supports an entry there and nothing in a slot describing this
  one. An empty declaration is not an assurance that every passage is about
  the referent. Binds every phase, the reconcile phase in particular —
  reconciling the two records against each other does not test what a
  value is about.

- **A list entry names exactly one entity** (v9, R7, #911): where the bundle
  states several, one entry each or none; a value that names a class of
  things where the schema asks for a thing, or joins separate names with
  "and", a slash or a comma, is a merge — unless the entity's own registered
  name contains the conjunction, in which case splitting it is the same
  error the other way.

- **The fragment rule does not reach an id the schema forces** (v9, R8,
  #803, #901): a file, a file collection, a data subset, a component
  dataset under `resources`, a software tool under `used_software`, a
  person given as an object — mint it on this record's own id and keep it
  stable; a person's id is the ORCID first (R5). For every other fragment
  the test stays the referent: an organisation, grant, award or program has
  one outside the record, so a fragment for it on the dataset's identifier
  is a claim, not a label — take the stated identifier, else leave `id`
  empty and carry the name; a creator or maintainer entry is a role whose
  id is the person's or organisation's own. A label this record mints sits
  on an identifier the evidence supplies for this dataset, its own id to
  prefer (a landing-page label needs a receipt, an own-id label does not,
  #1123); a fragment on another entity's identifier labels that entity.

- **An enumeration slot is filled only from a passage that states the
  category** (v9, R9, #830): never from a name, unit or position; `data_type`
  and `collection_type` are claims about how a thing is classified. Empty
  where no passage states it — except a required enum (`relationship_type`),
  where the entry itself is what the evidence must support — and the file
  enums `format`, `file_type`, `media_type`, `encoding` and `compression`,
  which the file's name and extension are the passage for.

- **`raw_data_format` names the form the data took before any processing
  this dataset applied, only where a passage states it** (v9, R10, #830):
  the release's standard, extension or pipeline format describes the
  release; where a passage says raw and released coincide, record both.

- **`principal_investigator` names a person the documents designate with
  that title** (v9, R11, #830): a lead, director, corresponding author,
  contact or first author is recorded as the role stated, in prose or in a
  slot for that role where one exists, never promoted; more than one, record
  each; none, empty.

- **A value states what a passage states, at the passage's own reach** (v9,
  R12, #830): a consequence (`scope_impact`) only where a passage draws it;
  a term from a keyword line, tag list, table header or menu attests that it
  appears — `keywords` is the one slot whose subject is that, and a keyword
  line fills it and nothing else.

- **Every entry in a list is a member of that list** (v9, R13, #830): a
  remark about the list — a sample marker, a continuation note, a column
  flag — is not a member; it goes in `description`, `source_caveats`, or
  nowhere.

- **An absence is not an entry, and a route is not a format** (v9, R14,
  #830): no correction published is not an erratum; access by request is a
  route and fills neither `future_guarantees` nor a distribution's `format`;
  the prohibition is the entry its `prohibition_reason` explains. A stated
  absence leaves the slot empty and, where worth keeping, goes in
  `source_caveats`.

The rule about there being no target slot count is the load-bearing one: it is
what makes a slot count an observation rather than a target. Named rather than
referred to by position, so inserting a rule cannot silently point this sentence
at a different one.
