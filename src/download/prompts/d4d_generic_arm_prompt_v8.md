# D4D generic-arm generation prompt — v8

**This is v7 plus one block of four rules.** Everything else is
byte-identical to `src/download/prompts/d4d_generic_arm_prompt_v7.md` apart
from the version stamp; a test asserts that the only difference is the block
marked `ADDED IN v8`. Four rules rather than one, deliberately: the v8 plan
(`notes/generic_v8_analysis_plan.md`) registers them as one configuration
with the depth-two schema digest (#916) and the inlined Person slots (#805),
and a v7-against-v8 comparison measures that package, not a rule.

## Why v8 exists

The twelve v7 production reviews found no pattern the v2–v6 rules did not
already forbid, and the same violations recurred — so v8 does not restate
prohibitions. Its four rules each name a mechanism the phase chain can act
on: which class-ranged attributes take an object and which a string, read
off the digest's own marking (R1); what a passage is *about and when* before
it is written as the referent's current state (R2); a figure the record
computes is stated as its computation with its inputs, never as a source's
figure (R3); and a roster is receipted entry by entry (R4). The evidence for
each is in the plan, not here, because this file is read by a generating
model.

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
    # Mode: four-phase project agent, generic-v8 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v8.md (identical for all projects)
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
    # Mode: four-phase project agent, generic-v8 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v8.md (identical for all projects)
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
  neighbouring field — the access route rather than the distribution formats,
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
- An identifier that names something outside this dataset — an organisation, a
  person, a publication, another dataset — is a fact about the world, subject to
  the same rule as any other fact: take it from the evidence or omit it. Do not
  supply one you recognise but the input documents do not state. A correct
  identifier the evidence does not contain is still an unsupported claim, and to
  every reader who was not present it is indistinguishable from an incorrect
  one. Naming an organisation the documents name is grounded; adding that
  organisation's registry identifier from your own knowledge is not.
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
  and an organisation by an organisation registry entry; a fragment appended to
  an organisation's identifier does not identify a person, it makes a false
  claim about that organisation.
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
  `principal_investigator` with its `name` and, where the evidence states
  them, `orcid`, `email` and `affiliation`. The earlier rule about scalar
  ranges governs scalar ranges only; a reconcile or repair phase must never
  reduce an object the digest asks for to a string, nor inflate a marked
  reference into an object, and an audit finding that an object in an
  object-ranged slot is "the thing, not its identifier" is wrong on its face.
- Before writing a value from a passage, name to yourself what the passage is
  about and when. A plan, a proposal, a protocol's intention or a future
  release is stated as such — in the tense the source uses — or omitted; it
  is never the current state of the dataset. A description of an earlier
  release, an archived version or a superseded file is a fact about that
  version, not about the referent's current release. A passage under a source
  the declared bundle names as related-but-distinct describes that other
  dataset; its facts belong only in `related_datasets`, never in the
  referent's own slots. The coverage receipt's snippet for a value must come
  from a passage about the referent, in the present.
- A figure the record derives from attested figures — a sum, a difference, a
  fraction, a count — is stated as the record's own computation, with the
  inputs it was computed from named beside it, never as a figure a source
  reported; a passage cannot receipt an arithmetic result it does not
  contain. Where the derived figure and a stated total disagree, record both
  and the difference in `source_caveats`, and do not resolve the disagreement
  by adjusting either.
- Where a slot is a list of objects the bundle states one by one — creators,
  funders, variables, file collections, files — each entry carries its own
  receipt naming the passage that states that entry. A roster receipted by
  one passage for one of its entries has receipted one entry; the others are
  values the record must not carry without a receipt of their own.

--- END ADDED IN v8 ---

--- ADDED IN v4 ---

- Where a slot's declared range is a scalar, populate it with the identifier of
  the thing it refers to, not with the thing itself. An object placed in a
  string-ranged slot fails validation and loses the reference it was meant to
  record, even where that thing is richly described elsewhere in the record.

--- END ADDED IN v4 ---


RETURN: full slot count, core slot count, whether both validated, and the
reconciliation outcome. Return data, not prose.
