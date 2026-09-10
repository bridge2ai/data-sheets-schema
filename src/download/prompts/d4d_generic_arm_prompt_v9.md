# D4D generic-arm generation prompt — v9

**This is v8 plus one block of nine rules.** The prompt body is
byte-identical to `src/download/prompts/d4d_generic_arm_prompt_v8.md` apart
from the version stamp; a test asserts that the only difference is the block
marked `ADDED IN v9`. This header is not part of the body and is not sent to
the model.

## Why v9 exists

The twelve v8 production reviews found two shapes the existing rules already
forbid and the model produced anyway, each because the rule referred to
something the model could not see or check.

R6 answers the first. v8's R2 says a passage about another dataset describes
that dataset — but until #932 the model was never shown *which* datasets
those are. It now receives the manifest's scope declaration: the referent,
the datasets declared related but distinct, and the bundle sources that
legitimately carry their documentation. R6 is the obligation that pairs with
that declaration, and it binds the reconcile phase, which is where these
leaks survived: three of the four instances on record were written in the
`full` phase and left standing by a reconciliation that checked the record
against itself rather than against the subject of each passage.

R7 answers the second. Rule-05 already says to emit one object per distinct
entity; the violations are not disagreement with the rule but a failure to
notice, and they share a signature — a value that reads as a category or a
conjunction where the schema asks for one entity. R7 names the signature, so
the check is something the model can run on a value it has just written
rather than a principle to hold in mind.

R8 through R14 were added before the first v9 run, from two sources: the
open half of the fragment-rule conflict (#803, #901) and the slot-level
adverse verdicts that recurred in three or more independent reviews across
the v6–v8 arms (#830, with the adjudication findings of 2026-09-01).

R8 answers the fragment conflict. The v6 rule says to mint a fragment only
where a value points at the part, but `File`, `FileCollection`,
`DataSubset`, `Person`, `Software` and a component `Dataset` under
`resources` are schema identifiers the record cannot omit (every forced-id
class reachable from `Dataset`; a test holds the list), and the core
derivation copies collection and file ids into its distributions and
matches top-level resources by id — so five of the six v6 rule-14 charges
charged the record with the schema (the sixth, CHORUS rep2's 68 fragments
on splits, purposes, limitations and software, was a correct charge for
the 57 on classes the schema does not force; the 11 on `used_software`
are the Software case R8 excuses). The other half is the unforced mint on a
referent outside the record: fragments for grants, awards and
organizations on the dataset's own DOI, and labels built on another
thing's identifier; a creator or maintainer entry is a role, whose id is
the person's or organization's own. R8 states the carve-out, the
ORCID-first person rule it defers to, and the referent test in one place,
and says how it refines the v5 minting base rather than silently narrowing
it. R9 exempts a required enum (`relationship_type`: the entry itself is
what the evidence must support) and the file enums the schema reads from
the file's name; R12 carves out `keywords`, the one slot whose subject is
that a term appears.

R9 (enumeration slots), R10 (`raw_data_format`), R11
(`principal_investigator`), R12 (consequence and keyword lines), R13 (a
list entry is a member) and R14 (an absence is not an entry, a route is not
a format) each name a trap the general rules already forbid and the model
produced anyway. Each is keyed to the slot or shape where it recurred, so
the check is something the model can run on the value it has just written.
Plan-as-done and entity merging recur too and are not repeated: the v8
tense rule and R7 already say them.

None of these is a new prohibition. The evidence for each is in the plan
note, not here, because this file is read by a generating model.

## Prompt body

Generate paired full and core D4D records for the {PROJECT} project.

READ FIRST, IN THIS ORDER, AND FOLLOW EXACTLY:

1. `.claude/agents/d4d-provenance-guard.md` — the factual evidence boundary.
   Enforce it in every phase.
2. `.claude/commands/d4d-full-core.md` — the four-phase playbook.

Execution mode: four-phase project agent. Phase 1 full generation, Phase 2 core
derivation from the validated full record, Phase 3 source/provenance audit,
Phase 4 strict reconciliation. Phase 2 must wait for a validated Phase 1 file.

VERSION LABEL — use verbatim in every output path: {LABEL}

ARM: {ARM}

DECLARED INPUT BUNDLE — your only source of dataset facts:
    {BUNDLE}

Full schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class
`Dataset`)
Core schema: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
(class `CoreDataset`)

OUTPUTS — do not write outside these three:

- Full:   `data/d4d_concatenated/{METHOD}/{LABEL}/{PROJECT}_d4d.yaml`
- Core:   `data/d4d_concatenated/{METHOD}_core/{LABEL}/{PROJECT}_d4d_core.yaml`
- Report: `data/d4d_concatenated/{METHOD}_core/{LABEL}/{PROJECT}_reconciliation.md`

HEADER BLOCK — use exactly:

    # D4D Datasheet for {PROJECT} Dataset
    # Generation Method: schema-grounded agentic, phase 1
    # Agent runtime: {RUNTIME}
    # Provider: {PROVIDER}
    # Model: {MODEL}
    # Mode: four-phase project agent, generic-v9 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v9.md (identical for all projects)
    # Arm: {ARM}
    # Source bundle: {BUNDLE}
    {MANIFEST_LINE}
    # Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
    # Prior D4D factual reuse: prohibited
    # Temperature: 0.0
    # Generated: {DATE}

CORE HEADER BLOCK — use exactly (it is not the full-record block with two
words changed; four lines differ and two have no counterpart above):

    # D4D Core Datasheet for {PROJECT} Dataset
    # Generation Method: derived by projection from the full record (#694)
    # Agent runtime: {RUNTIME}
    # Provider: {PROVIDER}
    # Model: {MODEL}
    # Mode: four-phase project agent, generic-v9 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v9.md (identical for all projects)
    # Arm: {ARM}
    # Source bundle: {BUNDLE}
    # Sources: data/d4d_concatenated/{METHOD}/{LABEL}/{PROJECT}_d4d.yaml
    {MANIFEST_LINE}
    # Schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
    # Prior D4D factual reuse: prohibited
    # Temperature: 0.0
    # Generated: {DATE}
    # Phase 4 reconciliation: completed

`# Sources:` is required, not decorative: it is what ties a core record to the
full record it was projected from, and the provenance guard checks for it. Write
`# Phase 4 reconciliation: completed` only once phase 4 has actually run.

AFTER Phase 4, write a LIVE provenance record:

    poetry run d4d provenance record --project {PROJECT} --method {METHOD} --label {LABEL} --input-bundle {BUNDLE}

VALIDATE both files before finishing:

    poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
    poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>

ABSOLUTE CONSTRAINT — do not read, open, grep, or consult any previously
generated D4D record, from any arm, any label, or any date. This includes
everything under `data/d4d_concatenated/` and any `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/`. Your only factual
inputs are the declared bundle above and the schema files. Prior-D4D reuse is a
defect under the provenance guard.

UNIFORM DECISION RULES — these apply identically to every project and every arm:

- Populate a slot only where the declared bundle supports it. Prefer omission
  over inference: an absent slot is a correct answer when the evidence is
  absent, and a plausible guess is not.
- Where the declared bundle contains sources that disagree, represent what the
  evidence states rather than silently selecting one. Do not merge distinct
  entities into a single claim.
- `Dataset` admits one referent. Choose the one the declared bundle best
  supports, state that choice in the reconciliation report, and hold to it
  consistently across both records.
- There is no target slot count, no expected density, and no expected
  relationship to any other arm or project. Apply your own judgment about what
  the evidence supports.

--- ADDED IN v2 ---

- When a slot's declared range is multivalued, emit one object per distinct
  entity. Collapsing several entities into a single object — several creators in
  one Creator, several uses in one intended_use — populates the slot without
  representing what it declares.
- Populate a slot with the information the field asks for, not with a pointer to
  where that information lives, and not with a statement that it is pending or
  absent. A value recording that documentation exists elsewhere has not answered
  the field; omit the slot instead.
- Read the slot's description before populating it. Where the evidence answers a
  neighboring field — the access route rather than the distribution formats,
  the release cadence rather than the future-use impacts — put it in the field it
  answers, or omit it.

--- END ADDED IN v2 ---

--- ADDED IN v3 ---

- When a slot's declared range is a class, populate the fields that class
  declares. Placing the content in a free-text field such as `description` while
  the declared fields — a name, an identifier, dates, affiliations — stay empty
  produces an object of the correct shape holding none of the structure it
  exists to carry. Where the evidence answers a declared field, populate that
  field rather than restating it in prose.

--- END ADDED IN v3 ---
--- ADDED IN v5 ---

- In a slot whose declared range is `uriorcurie`, never write a resolver URL
  where the schema declares a prefix: write the CURIE — a prefix, a colon, and
  the local part. A `ROR:` CURIE, not the ror.org URL; an `ORCID:` CURIE, not
  the orcid.org URL; a `doi:` CURIE, not the doi.org resolver form.
  **`uriorcurie` is the range this rule exists for**: its
  "uri" half is the fallback for an identifier that no declared prefix covers,
  never permission to expand one that a prefix does cover. Two records naming
  one thing in one form produce one identity; the same thing written as a
  prefix here and a resolver URL there produces two. Check the schema's
  declared prefixes and use one whenever it fits; a resolver URL in a
  `uriorcurie` slot whose prefix is declared is a defect even though it
  resolves.
  Three things this does not govern, and they are exempt entirely: a slot
  whose declared range is `uri` — not `uriorcurie` — takes a URL
  (`download_url` and `access_urls` are declared `uri`, and a CURIE there is
  wrong); a URL inside prose or a citation is text — leave both of these
  exactly as written; and a slot whose declared range is `string` follows its
  own description and pattern even when it holds an identifier — the `doi`
  slot takes the bare DOI, neither prefixed nor resolved.
- An identifier that names something outside this dataset — an organization, a
  person, a publication, another dataset — is a fact about the world, subject to
  the same rule as any other fact: take it from the evidence or omit it. Do not
  supply one you recognize but the input documents do not state. A correct
  identifier the evidence does not contain is still an unsupported claim, and to
  every reader who was not present it is indistinguishable from an incorrect
  one. Naming an organization the documents name is grounded; adding that
  organization's registry identifier from your own knowledge is not.
- An identifier that names a part of this dataset, and exists nowhere outside
  this record, is a label rather than a claim about the world — so no evidence
  can supply it and the rule above does not reach it. Mint it as a fragment on
  an identifier the evidence *does* supply, so the label stays traceable to
  something attested. This is the only case in which minting is right, and the
  test is whether the thing named has a referent outside this record: if it
  does, the rule above governs and you take the identifier from the evidence or
  omit it. Never invent a prefix — one the schema does not declare resolves to
  nothing, and where no fragment is possible either, a resolvable URL is the
  better answer. A person is identified by a personal-identifier registry entry
  and an organization by an organization registry entry; a fragment appended to
  an organization's identifier does not identify a person, it makes a false
  claim about that organization.
- Write American English throughout — characterize, organization, standardized,
  analyze, behavior, license. This governs the prose the record states, not
  quoted material: a title, a name or a direct quotation keeps the spelling its
  source used.
- Where two sources in the declared bundle disagree, prefer the one the input
  manifest ranks higher: state its value, and record in the caveat that the
  sources disagreed, what each said, and which was preferred. Where the
  disagreeing sources share the same rank the ranking cannot decide, so
  represent what the evidence states rather than selecting one. This refines
  the earlier rule about disagreement; it does not replace it.

--- END ADDED IN v5 ---

--- ADDED IN v6 ---

- Within the rule above, mint a fragment identifier for a part of this
  dataset only where another value in the record must point at that part —
  a split a task names, a subset a distribution cites, a collection a file
  belongs to. A part nothing points at is described in prose, not labeled:
  an identifier no value in the record uses is not a label, it is noise that
  reads as structure. Name the same part with the same fragment every time
  a value points at it, and mint nothing for a part that is only described.

--- END ADDED IN v6 ---

--- ADDED IN v7 ---

- After the full record, emit a second document: the coverage receipt for
  the declared bundle. The bundle is divided into chunks, each opening with
  a marker of the form `[cNNN]` on its own line. Write the record, then a
  line reading exactly `--- COVERAGE RECEIPT ---`, then a YAML document with
  `bundle_md5` (as given with the bundle) and `chunks`: one entry per marker,
  in order, each with `id` and a `status` from exactly these, each status
  with its own key — `extracted`, whose `extracted` key lists every
  `{slot, snippet}` pair the chunk supplied, the slot being the record path
  the value fills (a leaf, or an entry where one passage attests the whole
  entry) and the snippet a verbatim phrase copied from that chunk, never a
  lone short word; `redundant_with`, whose `chunks` key names the chunks
  that already receipted everything it holds; `nothing_relevant`, with a
  `reason`; or `duplicate_of`, whose `of` key names the chunk it repeats.
  Every value in the record that the bundle supplied appears in some
  chunk's receipt; a value with no receipt is one the record must not
  carry. The phase instruction shows the exact shape.

--- END ADDED IN v7 ---

--- ADDED IN v8 ---

- A slot whose declared range is a class takes one of two forms, and the
  schema digest says which: an attribute the digest marks `(reference — a
  string, not an object)` takes exactly that string, never an object; every
  other class-ranged attribute takes an object carrying the keys the digest
  lists for that class — a `Grant` under `grants` with its `grant_number`, an
  `Organization` under `affiliations`, a `Person` under
  `principal_investigator` with its `id`, its `name` and, where the evidence
  states them, `orcid`, `email` and `affiliation` (itself an object list, as
  the digest shows). The rule below about scalar ranges governs scalar ranges
  only; a reconcile or repair phase must never reduce an object the digest
  asks for to a string, nor inflate a marked reference into an object, and an
  audit finding that an object in an object-ranged slot is "the thing, not
  its identifier" is wrong on its face.
- Before writing a value from a passage, name to yourself what the passage is
  about and when. A plan, a proposal, a protocol's intention or a future
  release is stated as such — in the tense the source uses — or omitted; it
  is never the current state of the dataset. A description of an earlier
  release, an archived version or a superseded file is a fact about that
  version, not about the referent's current release. A passage whose subject
  is another dataset — a companion release, a sibling cohort, a dataset the
  documents cite — describes that other dataset; its facts belong only in
  `related_datasets`, never in the referent's own slots. The coverage
  receipt's snippet for a value comes from a passage about the value's own
  subject: the referent's current state for its own slots, the other dataset
  for an entry in `related_datasets`, that version for a statement about an
  earlier version.
- A figure the record derives from attested figures — a sum, a difference, a
  fraction, a count — is stated as the record's own computation, with the
  inputs it was computed from named beside it, never as a figure a source
  reported. It is receipted at its own path by the passages that state its
  inputs — a passage cannot receipt an arithmetic result it does not contain,
  and the receipt says so by citing the inputs. Where the derived figure and
  a stated total disagree, record both and the difference in
  `source_caveats`, and do not resolve the disagreement by adjusting either.
- Where a slot is a list of objects the bundle states one by one — creators,
  funders, variables, file collections, files — each entry carries its own
  receipt naming the passage that states that entry. A roster receipted by
  one passage for one of its entries has receipted one entry; the others are
  values the record must not carry without a receipt of their own.
- A `Person` the schema asks for as an object carries an `id`: the ORCID the
  evidence states, as a CURIE with the prefix ORCID, where it states one;
  otherwise a fragment minted on this record's own id (the record's id, a
  hash sign, then person and the name), which is the one case the fragment
  rule reaches for a person — the object exists only as this record's way of
  naming its contact. Never a mailto address or any other scheme as the id:
  the address belongs in `email`, beside the id, where the evidence states
  it. Look for the ORCID before minting — a person the documents list with
  an ORCID has one, and a fragment for that person is a second identity for
  one referent.

--- END ADDED IN v8 ---

--- ADDED IN v9 ---

- A value in one of the referent's own slots is supported by a passage whose
  subject is the referent. You are given a declared scope naming the referent
  and, where the project has any, the datasets declared related but distinct —
  with, for each and where the declaration states them, the slot its facts
  belong in and the bundle source carrying its documentation. Where it names a
  slot, a passage about that dataset supports an entry there; where it does
  not, the facts still belong with that dataset and not in a slot describing
  this one, however well the sentence would read there. A declaration listing
  no related dataset says only that none was declared: it is not an assurance
  that every passage in the bundle is about the referent, and the first
  sentence still governs. This binds every phase, and the reconcile phase in
  particular: reconciling the two records against each other does not test
  what a value is about, so check each value you keep against the subject of
  the passage behind it, not only against the rest of the record.
- A list entry names exactly one entity. Where the bundle states several, emit
  one entry each or none; never one entry whose value merges them. Two signs
  that you have merged: the value names a class of things where the schema
  asks for a thing — a plural or a collective noun standing where one
  organization, one person or one instrument belongs — or it joins what the
  sources state as separate names with "and", a slash or a comma. The test is
  the sources, not the punctuation: an entity whose own registered name
  contains "and", a comma or a slash is one entity, and splitting it is the
  same error in the other direction. Read back each entry you write in a
  multivalued slot and ask whether exactly one thing the sources name answers
  to it.
- The rule that a fragment is minted only where a value points at the part
  does not reach an id the schema forces. Where a class declares `id` as its
  identifier or requires it — a file, a file collection, a data subset, a
  component dataset under `resources`, a software tool under `used_software`,
  a person given as an object — the id exists because the object does, and
  leaving it out is a validation failure, not a fragment saved. Take the
  identifier the evidence states for that part first — a DOI, an ARK, a URL
  that names the file or the component dataset, in a form that is itself an
  identifier: a declared CURIE, an absolute URL, an ARK or a URN, and where
  the evidence states a resolver URL for a prefix the schema declares, that
  identifier written as the CURIE the rule above on declared prefixes
  requires, not as the URL — and mint a label only where it states none: on
  this record's own id where that id is itself such a form (the base rule
  below), stable across runs, never in place of an identifier the evidence
  supplies; and do not read that rule as a reason to omit the object. A
  person's id follows the rule for a person given as an object — the ORCID the
  evidence states first, a fragment only where it states none, on the base
  this rule sends the record to and never on a bare token. The ids of
  `file_collections` and of the files under them are copied into the core
  record's distributions, and top-level `resources` are matched to the core by
  id, so those ids are used whether or not the text points at them. For every
  other fragment the test stays the referent: an organization, a grant, an
  award, a program has a referent outside this record, so a fragment for it on
  this dataset's identifier is a claim about that identifier, not a label; and
  an entry under `creators` or `maintainers` is a role this record asserts
  about a person or an organization, whose id is that person's or
  organization's own identifier where the evidence states one. Take the
  identifier the evidence states; where it states none and the schema does not
  require an id, leave `id` empty and carry the name in `name`. A label this
  record mints sits on an identifier the evidence supplies for this dataset —
  which refines the rule that mints a label on an identifier the evidence
  supplies, without replacing it — and this record's own id is the base to
  prefer where it is itself an identifier form: a declared CURIE, an absolute
  URL, an ARK or a URN. A record whose own id is a bare token, or a CURIE on a
  prefix the schema does not declare, labels its parts on the dataset's DOI or
  landing page instead, never on the token, and where it carries neither, on a
  resolvable URL the evidence supplies for this dataset, which must be an
  identifier form like the others — an absolute URL with its scheme — the
  fragment rule's own license, a label minted on an identifier the evidence
  does supply. A label on the dataset's DOI or landing page is licensed too,
  but only on a form that is itself an identifier — the DOI as a declared
  CURIE (the doi prefix, a colon, the DOI), which is the form to write even
  where the evidence states the resolver URL, the page as an absolute URL with
  its scheme; a bare DOI string or a schemeless host with a label appended is
  a token, not an identifier. The own id is the one identity slot every record
  carries, whatever form the record gave it, where `page` and `doi` are
  optional; where it is an identifier form and not itself a shared root it
  names this dataset alone, while a landing page is often a site or project
  root shared with sibling releases, so a part labeled there cannot be told
  apart from a sibling's by its id alone. Where this record's own id is itself
  such a root, it is still the base to prefer: it is the identifier this
  record carries, and the label must stay stable; where the base this rule
  sends the record to already carries a fragment, the part's label is that
  fragment, a hyphen and the part's own label, on the same base — for a person
  under the person rule, that fragment, a hyphen, then person and the name —
  so the record's own discriminator is kept, and one identifier carries one
  fragment marker, never two. A fragment appended to another entity's
  identifier — an organization's, another dataset's — labels a part of that
  entity, not of this one.
- A slot whose declared range is an enumeration is populated only from a
  passage that states the category, in the source's own words or a plain
  restatement of them — never from what a value's name, unit or position
  suggests. A variable's `data_type` and a collection's `collection_type`
  are claims about how a thing is classified, and a passage that names the
  thing without classifying it supports the name and not the class. Where no
  passage states the category the slot stays empty — an empty enumeration
  slot is a gap the reader can see, a guessed one an error the reader cannot
  — except where the schema requires the slot, in which case the entry
  itself is what the evidence must support: a related dataset is recorded
  only where a passage states what the relation is. A file's `format`,
  `file_type`, `media_type` and `encoding`, and a file's or collection's
  `compression`, are read from the file the bundle names — its name and
  extension are the passage for them — and this rule does not reach those.
- `raw_data_format` names the form the data took before any processing this
  dataset applied, and only where a passage states that form. The standard
  the release conforms to, the extension the distributed files carry and the
  format a pipeline wrote are facts about the released data and belong in
  the slots that describe the release; where a passage states that the raw
  form and the released form are the same, record it in both; where the
  documents describe the release and say nothing of what preceded it, the
  slot stays empty.
- `principal_investigator` names a person the documents designate with that
  title, or its usual abbreviation, for this dataset or the study that
  produced it. A lead, a director, a corresponding author, a contact, a
  first author, the head of the group that hosts the data — each is a role
  the documents state, recorded as the role they state, in prose or in a
  slot for that role where the schema has one, and never promoted to
  principal investigator because the record has a slot for one. Where the
  documents designate more than one, record each; where they designate none,
  the slot stays empty.
- A value states what a passage states, at the passage's own reach. A
  consequence — what a limitation means for a use, what a gap does to a
  conclusion — goes in `scope_impact` or anywhere else only where a passage
  draws it; a limitation the documents state without its consequence is
  recorded as the limitation alone. A term taken from a keyword line, a tag
  list, a table header or a navigation menu attests that the term appears,
  not what it is about: `keywords` is the one slot whose subject is that the
  term appears, and a keyword line fills it and nothing else; any other
  value needs a sentence behind it.
- Every entry in a list is a member of that list: a variable under
  `variables`, a funder under `funders`, a file under the `resources` of a
  file collection. A remark about the list — that what is shown is a sample,
  that the list continues elsewhere, that one column flags something — is
  not a member and does not become an entry; it goes in `description`, or in
  `source_caveats`, or is omitted.
- An absence is not an entry, and a route is not a format. That no
  correction has been published is not an erratum and does not fill
  `errata`; that access is by request through a portal is a route and fills
  neither `future_guarantees` nor the `format` of a distribution; the reason
  a use is prohibited is its `prohibition_reason`, and the prohibition
  itself is the entry that reason explains, not the reason. Where the
  documents state that a thing is absent, the slot for the thing stays empty
  and the statement, where it is worth keeping, goes in `source_caveats`.

--- END ADDED IN v9 ---

--- ADDED IN v4 ---

- Where a slot's declared range is a scalar, populate it with the identifier of
  the thing it refers to, not with the thing itself. An object placed in a
  string-ranged slot fails validation and loses the reference it was meant to
  record, even where that thing is richly described elsewhere in the record.

--- END ADDED IN v4 ---


RETURN: full slot count, core slot count, whether both validated, and the
reconciliation outcome. Return data, not prose.
