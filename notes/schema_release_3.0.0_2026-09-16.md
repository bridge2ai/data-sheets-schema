# Schema release 3.0.0 and the neutral generation schema — 2026-09-16

This note resolves the two findings the [April-to-current schema
review](schema_changes_since_april_2026-09-16.md) placed before the final
generation freeze: the full/core schema had no release identity that
distinguished the current definitions from the ones labelled `2.0.0` on
2026-08-06 ([#1874](https://github.com/bridge2ai/data-sheets-schema/issues/1874)),
and the shared schema resources both generation arms consume carried
study-specific examples and descriptions under every profile, the neutral
one included ([#1875](https://github.com/bridge2ai/data-sheets-schema/issues/1875)).
No historical record, score, registration or source download is changed.

## Release identity (#1874)

| Entry point | Before | Now |
|---|---|---|
| `src/data_sheets_schema/schema/data_sheets_schema.yaml` (full, class `Dataset`) | `version: 2.0.0` | `version: 3.0.0` |
| `src/data_sheets_schema/schema/data_sheets_schema_core.yaml` (core, class `CoreDataset`) | no version | `version: 3.0.0` |

**How the core version relates to full.** The core schema is a projection
of the full schema: every core class and slot is defined in the modules the
full schema imports, and a core record is the deterministic derivation of an
audited full record (since 2026-08-27). The core therefore carries the full
schema's version and moves with it; it has no independent release line. The
provenance recorder now reads both declarations (`schema.declared_version`,
`schema.core_declared_version`, each with where it was read from) and writes
a `note` when they disagree, so a drift like the one #1874 found would be a
stated fact on every record rather than an assumption. Records written
before this carry only the full declaration.

**Why a major.** The comment beside the version field asks for a bump on
any class, slot or enum change; between 2026-08-06 and 2026-09-16 the label
stayed at `2.0.0` through the remaining narrative scalarization
(`4d2232560`), `DataGovernance` (`d740cc15c`), the data-standard vocabulary
(`ea12521a2`), anchored DOI validation (`9f2339746`) and Person inlining
(`816b44025`). Three of those reject records that `2.0.0` accepted, so the
current definitions are not a compatible revision of the August ones.
`3.0.0` names them as they stand at this commit; the exact schema revision
and the content hashes below remain the identity a manuscript should cite
beside the label.

**Regenerated artifacts.** Both merged schemas, the Python datamodel
(`version = "3.0.0"`), and the `project/` JSON Schema, JSON-LD and OWL
products were rebuilt from the edited sources with the pinned toolchain
(LinkML 1.9.3, LinkML Runtime 1.9.4). `schema_sync.check()` reports both
merged files in sync, and `tests/test_schema_release_identity.py` pins the
declarations, the generated artifacts and the recorder's reading of them.

## Migration implications (no historical record is rewritten)

A record valid under the August `2.0.0` may fail under `3.0.0` for these
reasons, in decreasing order of how often the April records hit them:

- **Narrative lists became scalar strings.** Sixty-five attributes lost
  `multivalued: true` (sampling strategy, preprocessing and cleaning detail,
  ethics-board detail, license terms, retention and update detail, and their
  nested kin). `preprocessing_details: ["step one", "step two"]` is now a
  validation error; the value is one block scalar. This is a representation
  change, not permission to omit documented facts.
- **Person references became inlined objects.** Principal investigator,
  creator, contact, ethics, license and governance contacts require a
  `Person` object with its required identifier; a bare name string fails.
- **DOI values must match the anchored bare form.** A URL-shaped DOI no
  longer passes by substring; the write-time normaliser rewrites resolver
  URLs in `uriorcurie` slots, but a record written by hand must state the
  bare DOI.
- **`Organization` and `Grant` identifiers became optional.** This direction
  is permissive: a record that invented an identifier to satisfy the old
  requirement still validates, and a new record need not invent one.
- **Additive fields.** `data_governance`, `conforms_to_standard`, `notes`,
  `source_caveats` (full and core) and `related_datasets` (core) are new
  places for facts the earlier shapes could not carry; their absence is
  never an error.

Migrating a historical record is a separately identified derived copy that
records its source and the migration applied. The April records, the v7/v8
and v9 arms and every later attempt keep their bytes, their recorded
validation verdicts and their scores; a verdict recorded under an earlier
schema is a fact about that schema, and re-validating under `3.0.0` reports
the current reading beside it (`d4d provenance recheck-validation`).

## Neutral generation schema (#1875)

The [neutral native probe](schema_changes_since_april_2026-09-16/neutral_native_probe.json)
found the merged schemas the native playbook selects under
`D4D_PROFILE=neutral` carrying AI-READI examples and a Bridge2AI-Voice
committee example. The sweep behind this change found more of the same
family than the issue listed: the whole `d4d:docExample` set had been
written against one study (Type 2 diabetes, continuous glucose monitoring,
retinal imaging and grading, a triple-balanced design), and three real IRB
protocol numbers and a real NIH award number sat among the examples.

**What changed.** Forty-six model-facing strings in the modules the two
generation roots import were replaced with neutral forms: the study names,
the `fairhub.io` platform URLs, the committee description and example, the
deprecated contact description's run reference, the `related_datasets`
description's companion-dataset example, the two vocabulary descriptions
that said "Bridge2AI standards" (they now say "a pinned standards
registry", which is what the profile mechanism supplies), and the example
family, which now describes a fictional cohort with wearable sensors,
imaging and clinical records, no disease named. The award example is a
form-only placeholder (`R01XX000000`) and the IRB example names no protocol
number. Comments in the source files were left alone: the generators drop
them, so they reach no model. The evaluation-summary schema, the generation
record and telemetry contracts, and the archival corpus are outside this
change, as the issue scopes them.

**What was verified.** `tests/test_neutral_generation_schema.py` parses the
import closure of both roots and scans every description, example,
annotation and comment field below schema level for the study names, the
platform, the retired identifiers and the design hallmarks; repeats the
probe on the resources `agentic_runtime.toolchain()` hands the executable
playbook under `neutral`; and scans the digest under both profiles. The
study profile's digest legitimately renders its pinned registry vocabulary,
which lists diabetes and retinal imaging as terms, so that digest is
scanned for study identity only. `tests/test_external_dataset_onboarding.py`
now also asserts that an external dataset's assembled requests carry no
registry list, no study name and none of the retired examples, and that
its record states `profile: neutral`. Schema namespace URIs
(`https://w3id.org/bridge2ai/…`) and the `B2AI_*` prefix declarations are
retained: they identify the schema, not a dataset.

## What moved and what did not

| Identity | Before | After |
|---|---|---|
| `data_sheets_schema.yaml` sha256 | `38e19f26a5490fd3…` | `6de786d36f04c27f…` |
| `data_sheets_schema_all.yaml` sha256 | `ea595c4bd45c54c1…` | `d723e8e726c0ba5f…` |
| `data_sheets_schema_core.yaml` sha256 | `0cdb2744a4025efa…` | `de607a078ede069b…` |
| `data_sheets_schema_core_all.yaml` sha256 | `7fcd7ddda719236…` | `0aba339b4d9da509…` |
| `Dataset` digest md5, `bridge2ai` | `6be1582236d9320b…` | unchanged |
| `Dataset` digest md5, `neutral` | `94859bbbe7fa2296…` | unchanged |
| `CoreDataset` digest md5, `bridge2ai` / `neutral` | `980ccdafe6762d45…` / `61c50be60e601f7d…` | unchanged |

The digest renders slot names, ranges, cardinality and the leading window
of each description, and none of the edited text sits in that window, so
**the API arm's instrument identity did not move** and the digest ledger
gains no entry. Every schema file hash moved, so `schema.full_sha256` and
`schema.core_sha256` on every new record, the schema files a registration
pins and the native playbook's toolchain hashes all move. That is the
condition boundary: a generation registered after this change pins
`3.0.0` and the hashes above, and no earlier registration or record is
re-attested. The plan note carries the dated amendment.

**The checked report blocks attest the previous hashes, and stay as
written.** Every `report_claims` block records the merged-schema hashes its
check ran under, and the corpus reproduction test required a fresh recompute
to reproduce them byte for byte, which any schema edit breaks; rewriting
the 278 blocks to today's hashes is what #1362/#1363 forbid. The release
history `src/data_sheets_schema/schema/release_history.yaml` now registers
each release's four hashes, and the test accepts a block that attests any
registered release while requiring the recompute to attest the newest one.
A future release adds its entry in the same change that moves the hashes.
