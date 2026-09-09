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
  declared bundle or omit it; do not supply an identifier you recognize but the
  bundle does not state. A correct identifier the evidence does not contain is
  still an unsupported claim, and to a reader who was not present it is
  indistinguishable from a wrong one. Naming an organization the bundle names is
  grounded; adding that organization's ROR from your own knowledge is not — the
  2026-08-13 arm did exactly this, supplying RORs for institutions the bundle
  names only in prose (#547). `grounding.absent` in the provenance record counts
  them.

- **An identifier for a part of this dataset, existing nowhere outside this
  record, is a label rather than a claim about the world**, so the rule above
  does not reach it: no evidence can supply it. The test is whether the thing
  named has a referent outside this record. Where it does not, hang the label
  off one the bundle does supply — a fragment on the identifier of the thing
  it is part of, `<the dataset's own DOI CURIE>#split-train`, rather than a new
  namespace (#531). A person is identified by an ORCID and an organization by a
  ROR; **a fragment appended to an organization's ROR does not identify a
  person**, it asserts something false about that organization.

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
  whose subject is the referent** (v9, R6, #913). You are given a declared
  scope naming the referent and, where the project has any, the datasets
  declared related but distinct — with, for each and where the declaration
  states them, the slot its facts belong in and the bundle source carrying
  its documentation. Where it names a slot, a passage about that dataset
  supports an entry there; where it does not, the facts still belong with
  that dataset and not in a slot describing this one, however well the
  sentence would read there. A declaration listing no related dataset says
  only that none was declared: it is not an assurance that every passage in
  the bundle is about the referent, and the first sentence still governs.
  This binds every phase, and the reconcile phase in particular:
  reconciling the two records against each other does not test what a
  value is about, so check each value you keep against the subject of the
  passage behind it, not only against the rest of the record.

- **A list entry names exactly one entity** (v9, R7, #911). Where the bundle
  states several, emit one entry each or none; never one entry whose value
  merges them. Two signs that you have merged: the value names a class of
  things where the schema asks for a thing — a plural or a collective noun
  standing where one organization, one person or one instrument belongs —
  or it joins what the sources state as separate names with "and", a slash
  or a comma. The test is the sources, not the punctuation: an entity whose
  own registered name contains "and", a comma or a slash is one entity, and
  splitting it is the same error in the other direction. Read back each
  entry you write in a multivalued slot and ask whether exactly one thing
  the sources name answers to it.

- **The rule that a fragment is minted only where a value points at the
  part (v6, #685) does not reach an id the schema forces** (v9, R8, #803,
  #901). Where a class declares `id` as its identifier or requires it — a
  file, a file collection, a data subset, a component dataset under
  `resources`, a software tool under `used_software`, a person given as an
  object — the id exists because the object does, and leaving it out is a
  validation failure, not a fragment saved: mint it on this record's own
  id, keep it stable, and do not read that rule as a reason to omit the
  object; a person's id follows the rule for a person given as an object
  (R5) — the ORCID the evidence states first, a fragment only where it
  states none. The ids of `file_collections` and of the files under them
  are copied into the core record's distributions, and top-level
  `resources` are matched to the core by id, so those ids are used whether
  or not the text points at them. For every other fragment the test stays
  the referent: an organization, a grant, an award, a program has a
  referent outside this record, so a fragment for it on this dataset's
  identifier is a claim about that identifier, not a label; and an entry
  under `creators` or `maintainers` is a role this record asserts about a
  person or an organization, whose id is that person's or organization's
  own identifier where the evidence states one. Take the identifier the
  evidence states; where it states none and the schema does not require an
  id, leave `id` empty and carry the name in `name`. A label this record
  mints sits on an identifier the evidence supplies for this dataset —
  which refines the rule that mints a label on an identifier the evidence
  supplies, without replacing it — and this record's own id is the base to
  prefer: a label on the dataset's landing page or DOI is licensed too,
  and a reader who follows this record's `id` finds its parts under it,
  which a label on another base does not give (#1123, #1147). A fragment
  appended to another entity's identifier — an organization's,
  another dataset's — labels a part of that entity, not of this one.

- **A slot whose declared range is an enumeration is populated only from a
  passage that states the category** (v9, R9, #830), in the source's own
  words or a plain restatement of them — never from what a value's name,
  unit or position suggests. A variable's `data_type` and a collection's
  `collection_type` are claims about how a thing is classified, and a
  passage that names the thing without classifying it supports the name
  and not the class. Where no passage states the category the slot stays
  empty — an empty enumeration slot is a gap the reader can see, a guessed
  one an error the reader cannot — except where the schema requires the
  slot, in which case the entry itself is what the evidence must support: a
  related dataset (`relationship_type`) is recorded only where a passage
  states what the relation is. A file's `format`, `file_type`, `media_type`
  and `encoding`, and a file's or collection's `compression`, are read from
  the file the bundle names — its name and extension are the passage for
  them — and this rule does not reach those.

- **`raw_data_format` names the form the data took before any processing
  this dataset applied, and only where a passage states that form** (v9,
  R10, #830). The standard the release conforms to, the extension the
  distributed files carry and the format a pipeline wrote are facts about
  the released data and belong in the slots that describe the release;
  where a passage states that the raw form and the released form are the
  same, record it in both; where the documents describe the release and
  say nothing of what preceded it, the slot stays empty.

- **`principal_investigator` names a person the documents designate with
  that title, or its usual abbreviation, for this dataset or the study that
  produced it** (v9, R11, #830). A lead, a director, a corresponding
  author, a contact, a first author, the head of the group that hosts the
  data — each is a role the documents state, recorded as the role they
  state, in prose or in a slot for that role where the schema has one, and
  never promoted to principal investigator because the record has a slot
  for one. Where the documents designate more than one, record each; where
  they designate none, the slot stays empty.

- **A value states what a passage states, at the passage's own reach** (v9,
  R12, #830). A consequence — what a limitation means for a use, what a gap
  does to a conclusion — goes in `scope_impact` or anywhere else only where
  a passage draws it; a limitation the documents state without its
  consequence is recorded as the limitation alone. A term taken from a
  keyword line, a tag list, a table header or a navigation menu attests
  that the term appears, not what it is about: `keywords` is the one slot
  whose subject is that the term appears, and a keyword line fills it and
  nothing else; any other value needs a sentence behind it.

- **Every entry in a list is a member of that list** (v9, R13, #830): a
  variable under `variables`, a funder under `funders`, a file under the
  `resources` of a file collection. A remark about the list — that what is
  shown is a sample, that the list continues elsewhere, that one column
  flags something — is not a member and does not become an entry; it goes
  in `description`, or in `source_caveats`, or is omitted.

- **An absence is not an entry, and a route is not a format** (v9, R14,
  #830). That no correction has been published is not an erratum and does
  not fill `errata`; that access is by request through a portal is a route
  and fills neither `future_guarantees` nor the `format` of a distribution;
  the reason a use is prohibited is its `prohibition_reason`, and the
  prohibition itself is the entry that reason explains, not the reason.
  Where the documents state that a thing is absent, the slot for the thing
  stays empty and the statement, where it is worth keeping, goes in
  `source_caveats`.

The rule about there being no target slot count is the load-bearing one: it is
what makes a slot count an observation rather than a target. Named rather than
referred to by position, so inserting a rule cannot silently point this sentence
at a different one.
