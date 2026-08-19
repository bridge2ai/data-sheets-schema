# D4D generic-arm generation prompt — v5

**This is v4 plus a block of five rules, and nothing else.** That is a
departure from the one-rule-per-version convention, and the reason is stated
under "Why v5 exists" rather than left to be inferred. The
substitution fields, outputs, header block, constraints, the four original rules
earlier additions are byte-identical to
`src/download/prompts/d4d_generic_arm_prompt_v4.md` apart from the version stamp;
a test asserts that the only difference is the block marked `ADDED IN v5`.

## Why v5 exists

Five rules, not one. Two of them are not new instructions at all — they already
reach the agentic arm through the playbook and reach the API arm through
nothing, which is the divergence #545 measured. Bringing them here is a parity
fix; a condition whose two runtimes read different rules is not one condition.

- **American English** (#502) and **CURIE form** were added to
  `.claude/commands/d4d-full-core.md` mid-arm, deliberately, to avoid rotating a
  pin while runs were in flight. That was the right call then and leaves the two
  paths unequal until a version boundary, which this is.

The other two are new, and they are one subject: where an identifier may come
from.

- **An identifier is a fact and must come from the evidence.** VOICE rep1
  supplied 19 RORs that appear nowhere in its bundle and CM4AI rep3 another ten
  (#547). Every one is correct — `ror.org/032db5x82` really is the University
  of South Florida, whose name the bundle states 16 times. The run learned the
  institution from the evidence and the identifier from memory. The uniform
  rules already say to prefer omission over inference for facts; nothing said
  that an identifier is one.
- **A minted identifier hangs off an attested one.** #531 found one namespace
  written five ways — 1,094 VOICE values across five spellings. Counting the
  same way across every project while implementing this brought the total to
  roughly 12,000 minted ids, invented because
  the schema never offered a prefix. Declaring all the spellings would make
  every value valid and join nothing. The remedy that needs no new namespace is
  the pattern the corpus already contains and the grounding check already
  recognises: a fragment on the dataset's own identifier.

These two would be incoherent apart. A rule forbidding unattested identifiers,
without saying what to write instead, would push a model toward inventing a
local namespace — the defect #531 records.

## Why v5 is not a clean single-rule increment, and what that costs

The v2→v3→v4 series each isolated one rule so a delta could be attributed to it.
v5 cannot: five rules move together, and a v4-against-v5 comparison measures
their sum.

That is accepted rather than hidden. Two of the four are parity fixes whose
effect on the agentic arm is by construction nil — they are already there — so
the arms are the natural place to separate them. Any attribution finer than
"the v5 block" is not available from this comparison, and no analysis should
claim it.

## Why these additions are generic and not priming

Measured against the taxonomy in `.claude/commands/d4d-full-core.md`:

- it applies identically to every project, naming no project, dataset or input
  set;
- it states no target count, no expected density, and no expected relationship
  to any other arm — it is a decision rule, not an outcome expectation;
- it concerns the schema, which every arm shares.

## What is NOT in this file, deliberately

The prediction that these rules reduce ungrounded identifiers without
suppressing legitimate ones. Writing it here would instruct the model to produce
the result the run is meant to test. It belongs in the v5 analysis plan,
registered before any generation run.

## Relationship to earlier versions

None is superseded and none may be edited once run. v4 against v5 measures the
whole v5 block and not any rule within it — see above.

## Prompt body

Generate paired full and core D4D records for the {PROJECT} project.

READ FIRST, IN THIS ORDER, AND FOLLOW EXACTLY:

1. `.claude/agents/d4d-provenance-guard.md` — the factual evidence boundary.
   Enforce it in every phase.
2. `.claude/commands/d4d-full-core.md` — the four-phase playbook.

Execution mode: four-phase project agent. Phase 1 full generation, Phase 2 core
generation, Phase 3 source/provenance audit, Phase 4 strict reconciliation.
Phase 2 must wait for a validated Phase 1 file.

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
    # Mode: four-phase project agent, generic-v5 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v5.md (identical for all projects)
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
    # Generation Method: schema-grounded agentic, phase 2
    # Agent runtime: {RUNTIME}
    # Provider: {PROVIDER}
    # Model: {MODEL}
    # Mode: four-phase project agent, generic-v5 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v5.md (identical for all projects)
    # Arm: {ARM}
    # Source bundle: {BUNDLE}
    # Sources: {BUNDLE} + data/d4d_concatenated/{METHOD}/{LABEL}/{PROJECT}_d4d.yaml
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

- In a slot whose declared range is an identifier, never write a resolver URL
  where the schema declares a prefix: write the CURIE — a prefix, a colon, and
  the local part. Two records naming one thing in one form produce one
  identity; the same thing written as a prefix here and a resolver URL there
  produces two. Check the schema's declared prefixes and use one whenever it
  fits; a resolver URL in such a slot is a defect even though it resolves.
  Two things this does not govern, and they are exempt entirely: a slot whose
  declared range is a URL takes a URL, and a URL inside prose or a citation is
  text. Leave both exactly as written.
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

--- ADDED IN v4 ---

- Where a slot's declared range is a scalar, populate it with the identifier of
  the thing it refers to, not with the thing itself. An object placed in a
  string-ranged slot fails validation and loses the reference it was meant to
  record, even where that thing is richly described elsewhere in the record.

--- END ADDED IN v4 ---


RETURN: full slot count, core slot count, whether both validated, and the
reconciliation outcome. Return data, not prose.
