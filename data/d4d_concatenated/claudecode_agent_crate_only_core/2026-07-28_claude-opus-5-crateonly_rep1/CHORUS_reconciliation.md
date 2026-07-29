# CHORUS full/core reconciliation — crate-only arm, rep1

| | |
|---|---|
| Run label | `2026-07-28_claude-opus-5-crateonly_rep1` |
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | `claude-opus-5[1m]` |
| Mode | four-phase project agent, crate-only |
| Temperature | 0.0 |
| Generated | 2026-07-28 |
| Allowed factual input | `data/preprocessed/concatenated/CHORUS_crate_only.txt` (only) |
| Full record | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/CHORUS_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CHORUS_d4d_core.yaml` |
| Prior D4D factual reuse | prohibited; none occurred |

## Referent

**The CHoRUS RO-Crate Package, version 1.0 Beta — DOI `10.18130/V3/XNBOPG`.**

The crate root entity (`ark:59853/rocrate-chorus-ro-crate-package/`) is the only
subject the bundle describes in its own right, and the AI-readiness assessment is
titled "AI-Ready Score for CHoRUS RO-Crate Package", confirming the same referent.
The crate's own citation names this as "The Bridge2AI CHoRUS for Clinical Care AI
Dataset … version 1.0 Beta. Harvard Dataverse, Apr. 2026", so the record documents
the deposited interim release, not the CHoRUS network or the full cohort. The two
sub-crates the root declares in `hasPart` — EHR and Waveforms — are modelled as
`resources`, which is the schema slot whose range is `Dataset` (full) /
`CoreDataset` (core), giving a clean full→core projection.

The `completeness` field ("Interim release with partial data. Not all patients in
the CHoRUS full cohort are included. No DICOM images are included.") is what makes
this referent choice load-bearing: the record must not be read as describing the
CHoRUS cohort as a whole. It is carried in `status` and again as a
`coverage_limitation`.

---

## Phase 3 — source and provenance audit

### Provenance boundary

Files read during this run, in full:

- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md` (procedure)
- `data/preprocessed/concatenated/CHORUS_crate_only.txt` (**sole factual source**)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`,
  `data_sheets_schema_core_all.yaml`, `D4D_Core.yaml` (structure only, read via
  `SchemaView` induced-slot inventories rather than by copying any example)
- `src/data_sheets_schema/d4d_pair_consistency.py` (validator behaviour)

No prior full or core D4D record, no evaluation, no reconciliation report, no
`CHORUS_preprocessed*.txt`, nothing under `data/preprocessed/individual/CHORUS/`,
`data/raw/CHORUS/`, or `data/ro-crate_packages/CHORUS/`, and no live web content
was opened. Output directory listings were consulted for **names only**, to confirm
no CHORUS file already existed at the target paths (none did); no prior file
contents entered context. Structure was derived exclusively from the schemas; no
`d4d:docExample` value was copied.

### Corrections made in Phase 3

Three verbatim-fidelity defects were found in the Phase 1 full record and fixed
there first, then re-projected into core:

| # | Slot(s) | Was | Now |
|---|---|---|---|
| 1 | `ip_restrictions.restrictions[0]` and both `resources[*].ip_restrictions` | `(c) 2026 THE GENERAL HOSPITAL…` | `© 2026 THE GENERAL HOSPITAL…` (crate `copyrightNotice`) |
| 2 | `description`, `confidential_elements[0].confidentiality_details[3]`, `regulatory_restrictions.other_compliance[1]` | `NIST 800-53-aligned` (hyphen) | `NIST 800-53–aligned` (en dash, as in crate `description`) |
| 3 | `creators[].affiliations[].name` (Seattle Children's, Nationwide Children's) | straight apostrophe | `’` (curly, as in the crate affiliation legend) |

A process defect was also caught and corrected: the first core assembly picked up a
pre-correction body from the session-shared scratchpad directory, which another
concurrently running agent had also written to. The core record was rebuilt from a
private scratchpad path and byte-compared against a fresh schema-derived projection
of the corrected full record before Phase 4 (`core now matches private derivation:
True`). All later steps used the private path.

### Considered and rejected

- **`page`** — the dataset landing page `https://chorus4ai.org/dataset/` appears in
  the crate's `license` string and as the sub-crates' `contentUrl`. Asserting it as
  `page` would be my classification of a `contentUrl`, not a crate statement. The
  URL is already carried verbatim in `download_url`, `external_resources`, and
  `license_and_use_terms.license_terms`. Left empty.
- **`publisher`** — the crate gives `"B2AI CHoRUS"`, which is not a URI or CURIE and
  cannot honestly occupy a `uriorcurie` slot. Recorded instead as a `maintainers`
  entry whose description states it is the crate's publisher.
- **`issued`** — the schema enforces `date-time` format; `2026-04-03` is a date and
  the crate states no time. Rather than invent `T00:00:00Z`, the publication date is
  carried in `distribution_dates.release_dates` as a string.
- **`total_size_bytes` at root** — the crate's root `contentSize` is `"1.2 tb"`, a
  rounded figure. Populating an integer byte count from it would assert false
  precision. Left empty; see the unit note below for the sub-crates.
- **`is_tabular`** — the release mixes TSV (OMOP), WFDB, and notebooks. The crate
  makes no tabularity claim and no single answer is true of the package.
- **`is_random`** — the crate's "not randomized" describes study design (real-world
  clinical data, not an RCT), not sampling randomness. Reading it as
  `is_sample.is_random: false` would be a misreading, so the field is left empty
  while `is_representative: false` is populated from the explicit generalizability
  and referral-bias statements.

### Judgment calls that populate a field (flagged, not hidden)

These are the places where crate text was mapped onto a constrained schema value.
In every case the verbatim source string is preserved elsewhere in the same object.

1. **Sub-crate byte counts.** `contentSize` `"18.136671 mb"` → `18136671` and
   `"1.201567472832 tb"` → `1201567472832`. Both decimal expansions land on exact
   integers under SI (10⁶ / 10¹²) and on non-integers under binary units, which is
   what justifies the decoding. Recorded on `resources[*].total_size_bytes` (full
   only — `CoreDataset` has no such slot).
2. **`total_file_count: 1477`** from the AI-readiness `verifiable` metric,
   "99% of files have checksums (1469/1477)". This is a count of files *in the
   crate* (which also reports 1,468 documented datasets, 44 schemas, 1 software
   instance, 2 computation steps), not necessarily of data instances. The full
   breakdown is preserved verbatim in `relationships.relationship_details`.
3. **`confidentiality_level: confidential`** from `"HL7:2V (very restricted)"`. The
   schema enum offers only unrestricted / restricted / confidential; the verbatim
   HL7 value is kept in `regulatory_restrictions.description` and in
   `confidential_elements`.
4. **`bias_type` and `limitation_type` enum assignments** for the six `rai:dataBiases`
   and seven `rai:dataLimitations` bullets. The crate supplies prose only; each
   bullet's exact text is preserved in `bias_description` /
   `limitation_description`, so the enum is additive and reversible.
5. **`is_deidentified.identifiable_elements_present: false`** from `deidentified: true`
   plus "Removal or tokenization of direct identifiers".
6. **`status`** carries the crate's `completeness` string; **`conforms_to`** carries
   `https://w3id.org/ro/crate/1.2`, which the crate states on the metadata
   descriptor rather than on the dataset entity.
7. **`informed_consent`** holds "IRB approval or waiver as appropriate" and the human
   subject exemption. `consent_obtained` is deliberately left empty — the crate never
   states that individual consent was obtained, and the object's description says so.

### Source-internal inconsistencies — preserved, not silently repaired

- **Date format.** Root `datePublished: "2026-04-03"` but `releaseDate: "03/04/2026"`;
  the Waveforms sub-crate uses ISO `2026-04-03` while the EHR sub-crate uses
  `"03/04/2026"`. `03/04/2026` is ambiguous in isolation; the ISO fields and the
  citation ("Apr. 2026") resolve it to 3 April 2026, which is what
  `distribution_dates` records, with the raw variant noted in each object's
  description.
- **Access URL.** Root `contentUrl: http://chorus4ai.org/dataset` (http, no trailing
  slash) vs both sub-crates' `https://chorus4ai.org/dataset/`. Each entity's own
  value is recorded on that entity; not a contradiction.
- **Licence string.** Root: "Data Use Agreement available at
  'https://chorus4ai.org/dataset/'"; sub-crates: "See Data Use Agreement". Same
  instrument, different wording; both preserved.
- **PI string.** Root `principalInvestigator: "Eric Rosenthal, EROSENTHAL@mgh.harvard.edu"`;
  sub-crates: `"PI Eric Rosenthal  EROSENTHAL@mgh.harvard.edu"` (double space).
  Both kept verbatim on their respective entities.
- **`humanSubjectExemption`: "HIPAA exemption 4 ((45 CFR 46.104(d)(4))"** — the
  citation is to the Common Rule (45 CFR 46), not HIPAA, and the parentheses are
  unbalanced. Recorded verbatim; the mislabel is the crate's, and correcting it
  would import outside knowledge this arm forbids.
- **`rai:dataBiases` and `rai:potentialBiases` are byte-identical** in the crate;
  they are represented once, in `known_biases`.
- **`rai:dataReleaseMaintenancePlan` and `rai:maintenancePlan` are byte-identical**;
  represented once, in `updates`, with the archiving clause also in `retention_limit`.
- **Size arithmetic.** Root `"1.2 tb"` ≈ Waveforms `1.201567472832 tb` + EHR
  `18.136671 mb`. Consistent to the precision given.

### Validation after Phase 3 corrections

```
poetry run linkml-validate -s .../data_sheets_schema_all.yaml -C Dataset <full>            → No issues found
poetry run linkml-term-validator validate-data <full> --schema ... --target-class Dataset  → ✅ Validation passed
poetry run linkml-validate -s .../data_sheets_schema_core_all.yaml -C CoreDataset <core>   → No issues found
poetry run linkml-term-validator validate-data <core> --schema ... --target-class CoreDataset → ✅ Validation passed
```

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at run time with LinkML `SchemaView` from `Dataset` and `CoreDataset`
(no hand-written field list):

- **76 schema-identical slots** — must be deeply equal and identically present.
- **1 projected slot** — `resources` (`Dataset` in full, `CoreDataset` in core).
- **8 full-only root slots**, correctly absent from core because `CoreDataset` does
  not declare them: `citation`, `total_file_count`, `relationships`, `splits`,
  `related_datasets`, `direct_collection`, `participant_privacy`,
  `third_party_sharing`.
- **2 core-only slots** — `distributions`, `dialect` — both empty (see below).

Core was built in Phase 2 by projecting the Phase 1 full record through the
`CoreDataset` induced-slot inventory, so identity holds by construction; the
validator then confirms it independently.

### Commands and results

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
  → PASS: 76 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
  → PASS: 76 schema-identical slots; projected slots=['resources']   (exit 0)
```

No errors and **no warnings** were emitted. `--sync-core` produced no content change
beyond appending `# Phase 4 reconciliation: completed` to the core header (line 23),
confirming the Phase 2 projection was already canonical.

### Resource projection

Both records carry the same two resource ids with equal coverage:

| id | name | full-only slots dropped in core |
|---|---|---|
| `08cf7419-b94d-4508-8f64-c99c557351d7` | CHoRUS RO-Crate EHR SubRoCrate | `citation`, `total_size_bytes` |
| `b9b41c72-0895-4ec2-9e39-8de2a83abcd6` | CHoRUS RO-Crate Waveforms SubRoCrate | `citation`, `total_size_bytes` |

Every schema-identical nested slot (`name`, `description`, `version`, `license`,
`download_url`, `keywords`, `creators`, `funders`, `ip_restrictions`,
`license_and_use_terms`, `distribution_dates`) is deeply identical in both records.

### Semantic review of related, non-identical content

- **`file_collections` ↔ `distributions`** — both empty, so no mapping exists to
  conflict. This is a direct consequence of the input: the bundle's crate JSON has
  its per-file inventories collapsed, so no path, per-file byte count, checksum,
  media type, or compression is available for any individual file. The aggregate
  facts that survive (1,477 files, 1,469 checksummed, formats `.ipynb` /
  `text/tab-separated-values` / `wfdb`) are recorded in `total_file_count`,
  `relationships`, and `distribution_formats` instead. Emitting a synthetic
  single-entry `file_collections` was rejected: it would have forced an equally
  synthetic `distributions` entry (the validator errors when one exists without the
  other) and would have asserted a distribution that the crate does not describe.
- **`total_file_count` / `total_size_bytes` vs distribution-level values** — no
  distribution-level values exist, so no scope comparison is possible. Root
  `total_size_bytes` is empty by design; the two sub-crate byte counts are full-only
  and are not contradicted anywhere in core.
- **`dialect`, formats, `is_tabular`** — `dialect` empty (no delimiter, quoting,
  or header convention stated anywhere in the crate); `is_tabular` empty in both;
  `distribution_formats` is a schema-identical slot and is byte-identical across the
  pair.
- **Identity / version / access facts across the pair** — `id`, `doi`, `version`
  (`1.0 Beta`), `license`, `status`, `title`, `download_url`, `conforms_to`,
  `keywords` all identical between full and core, and internally consistent with
  `version_access.latest_version_doi` (same DOI), both resources' `version`
  (`1.0 Beta`), and `distribution_dates` (`2026-04-03` at root and on both
  resources). `related_datasets` targets (full only) match the two `resources` ids
  exactly.
- **Historical vs current release** — only one release exists (1.0 Beta); the crate
  describes a versioning and deprecation policy but no prior version, so there is no
  historical/current value pair to disambiguate.
- **Identifier hygiene** — 178 ids across the full record; the only repeated ids are
  the 15 `Organization` ids shared by co-authors at the same institution, and every
  repetition carries an identical name (checked programmatically). 42 `creators`
  = 41 named authors + 1 collective entry for the CHoRUS network.

### Post-Phase-4 validation

All four validations re-run after synchronization: full and core both
`No issues found` and `✅ Validation passed`.

### Provenance record

```
poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_crate_only.txt
```

→ `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CHORUS_provenance.yaml`,
`record_mode: live`, model `claude-opus-5[1m]`, input bundle md5
`06ad867c85e1d1ba0818c34e5bbaec29`, full 56 slots / core 48 slots.

---

## What the crate could NOT support at all

56 of the 94 `Dataset` slots are populated; **38 are empty**. Grouped by D4D area:

**Composition — largely unsupported.** No `variables` (the crate reports "44
schema(s) documented" but the reduced metadata exposes no variable-level entries),
no `subsets`, no `subpopulations`, no `content_warnings`, no `parent_datasets`. No
instance *counts* anywhere: patients, encounters, records, waveform hours, and site
count are all absent, so `instances` carries modality descriptions with no
cardinality. There is no cohort definition, no inclusion/exclusion criteria, and no
demographic breakdown.

**Distribution mechanics — unsupported.** No `file_collections`, no per-file paths,
formats, checksums, or byte counts; no `compression`; no `conforms_to_class` or
`conforms_to_schema` (the OMOP and WFDB standards are named only in prose, with no
version or URI); no `total_size_bytes` at package level beyond a rounded "1.2 tb".
Core's `distributions` and `dialect` are empty for the same reason.

**Collection timing — entirely absent.** No `collection_timeframes`: the crate never
states when the underlying clinical data were generated or over what period. For a
retrospective real-world clinical dataset this is a significant gap, and it is one
the crate alone cannot close.

**Consent workflow — thin.** `collection_notifications`, `collection_consents`, and
`consent_revocations` are all empty; the crate offers only "IRB approval or waiver
as appropriate" plus an exemption citation, which is recorded under
`informed_consent`. There is no notification mechanism, no withdrawal mechanism, and
no consent scope. `at_risk_populations` is empty — pediatric institutions appear in
the author affiliations, but that is an affiliation fact, not a statement about the
data, and inferring pediatric content from it would be exactly the kind of gap-fill
this arm forbids. `participant_compensation` is empty (unsurprising for repurposed
clinical data, but the crate does not say so).

**Annotation and labeling — entirely absent.** No `labeling_strategies`,
`annotation_analyses`, `machine_annotation_tools`, `imputation_protocols`, or
`cleaning_strategies`. The crate's bias list refers to "label assignment", but no
labeling protocol, annotator, agreement statistic, or imputation rule is described
anywhere.

**Uses in the wild — absent.** No `existing_uses`, no `use_repository`, no
`other_tasks`, no `future_use_impacts`. The crate documents *intended* use richly
(via `rai:intendedUseCases`) and discouraged use explicitly, but says nothing about
any actual use, publication, or downstream artifact.

**Motivation gap statement — absent.** `addressing_gaps` is empty. The crate states
purpose ("improve recovery from acute illness") but never frames a gap the dataset
closes.

**Maintenance detail — partial.** No `errata` (release notes are promised as the
channel for known issues, but no erratum or URL exists), no `extension_mechanism`
(no contribution route is described), and no update *frequency* — the plan is
qualitative ("Versioned dataset releases e.g., CHoRUS vX.Y)") with no cadence.

**Bibliographic housekeeping — absent.** `created_on`, `last_updated_on`,
`created_by`, `modified_by`, `was_derived_from`, `language`, `page`, `publisher`
(unusable as `uriorcurie`), and `issued` (date-only, see above) are all empty.

### Where the crate is genuinely strong

The Croissant RAI fields carry this record. Ethics, governance, access conditions,
privacy technique, bias, limitation, intended and discouraged use, de-identification
method, and the maintenance plan are all populated directly from crate text with
little interpretation — `rai:conditionsOfAccess`, `rai:personalSensitiveInformation`,
`rai:dataBiases`, `rai:dataLimitations`, `rai:intendedUseCases`, `rai:dataCollection`,
and `rai:maintenancePlan` between them fill most of the Ethics, Data Governance,
Uses, and Maintenance modules. Attribution is unusually complete for a single
structured source: 41 named authors with a resolvable 15-organization affiliation
legend, a named PI, a named contact, a named governance contact, an IRB with
protocol number and full postal contact, and an exact grant number.

The shape of the result is therefore lopsided rather than uniformly sparse: a crate
carrying RAI properties supports the *narrative governance* half of a datasheet well
and the *quantitative composition and distribution* half hardly at all.

---

## Completion checklist

| Criterion | Status |
|---|---|
| Full passes schema + term validation | ✅ |
| Core passes schema + term validation | ✅ |
| All structure schema-derived | ✅ (`SchemaView` induced slots; no prior record read) |
| 76 schema-identical slots deeply identical and identically present | ✅ |
| Projected `resources` reviewed | ✅ (2/2 matched, equal coverage) |
| Related content mapped and reviewed | ✅ (no unresolved contradictions) |
| Core header names both inputs | ✅ |
| Both headers state prior D4D reuse prohibited | ✅ |
| Core header contains `Phase 4 reconciliation: completed` | ✅ (line 23) |
| Live provenance record present | ✅ `record_mode: live` |
| No prior-run D4D, evaluation, or report used | ✅ |

Informational only, never a quality gate: full 1,194 lines / 56 populated root
slots; core 874 lines / 48 populated root slots.
