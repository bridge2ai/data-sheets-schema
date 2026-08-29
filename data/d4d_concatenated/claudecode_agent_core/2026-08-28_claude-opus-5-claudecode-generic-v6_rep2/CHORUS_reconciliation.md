# CHoRUS — Phase 3/4 reconciliation

**Run label:** `2026-08-28_claude-opus-5-claudecode-generic-v6_rep2`
**Arm:** BASELINE (input documents only)
**Mode:** four-phase project agent, generic-v6 prompt
**Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
(md5 `9b2ef4b65d67957f79362266cab0bc7a`, 1698 lines, 8 chunks)

**Artifacts**

| artifact | path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_d4d_core.yaml` |
| Coverage receipt | `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_coverage_receipt.yaml` |
| This report | `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_reconciliation.md` |

## Referent

`Dataset` admits one referent. The record is about the **CHoRUS dataset**, and its
identifier is `https://chorus4ai.org/`. That is what the input manifest's `scope:`
block declares for this project (`referent: CHoRUS dataset`, `referent_id:
https://chorus4ai.org/`, `related_but_distinct: []`), with the manifest's own note
that no dataset DOI appears in any CHoRUS source document, so the project site is
the identifier the records use. The choice is held consistently across both
records; every minted identifier in the record is a fragment on that base.
`d4d download scope --check --project CHORUS` reports 140 records checked and none
about a dataset its project declares distinct.

Facts about the *project* — the NIH award, the leadership team, the consortium's
size — are recorded as dataset-creation facts (`funders`, `creators`), not as a
second referent. Facts about the **AIM-AHEAD Bridge2AI for Clinical Care Training
Program**, which is a consumer of the dataset rather than the dataset, are held in
`external_resources[1]` and are not merged into the dataset's own claims; the
program's curriculum, stipend, eligibility rules and application cycle — most of
bundle chunks c004 and c005 — are deliberately not extracted at all.

## Phase 1 — full generation and coverage receipt

Chunk manifest `data/preprocessed/chunks/CHORUS_chunks.yaml` reported `current`
against the bundle before reading began. All 8 chunks were read with the
file-reading tool in manifest order, each chunk's receipt entry written before the
next chunk was opened.

```
poetry run d4d bundle chunk --check --project CHORUS      → current
poetry run linkml-validate -s .../data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema ... --target-class Dataset
poetry run d4d receipts check --label <LABEL> --project CHORUS --strict
```

Receipt result: **chunks 8/8 reviewed · snippets 109/109 verified · slots 136/194
with a receipt (87 exempt) · no findings.**

Two chunks are `extracted` with a small number of pairs and a note saying why the
rest was not taken: c004 and c005 are the training program's curriculum and
application logistics. c001 is `nothing_relevant` — it is the concatenation
preamble and table of contents.

Three snippets failed the first receipts run and were repaired before Phase 2:
two carried a `...`-part below the three-character floor (`9`, `14`, both
recorded instead as the contiguous line pair they come from), and one listed its
parts out of chunk order. No snippet was found in a chunk other than the one it
was filed under.

## Phase 2 — core derivation

The core is derived, not generated. One command, no model judgement:

```
poetry run d4d derive core --full <full> --out <core>
```

Derivation facts as the command printed them:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_d4d.yaml",
          "md5": "e5c190049c886030f2ea7146194756b5"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The `md5` above is the corrected full record, from the Phase 4 re-derivation. The
first derivation (before the Phase 3 corrections) ran against md5
`54165ff25f86ff92d15869083528499e`.

The full record carries no `file_collections`, so the core carries no
`distributions` and no derived `dialect`. That is the honest outcome: the bundle
describes data types, standards and volumes, and says nothing about files, paths,
counts or sizes at file level.

## Phase 3 — source and provenance audit

### Provenance

No prior generated D4D record was read, opened, grepped or consulted, from any
arm, label or date. The factual inputs for this run were the declared bundle, the
input manifest (`scope:`, `naming:`, `source_priority`, the CHORUS source list),
the two schema files, and the repository's own playbooks
(`d4d-provenance-guard.md`, `d4d-full-core.md`, `d4d-agent.md`,
`d4d-uniform-rules.md`). No evaluation report or reconciliation report from any
earlier run was consulted.

### Source disagreements, resolved by the declared ranking

The bundle holds four sources at three tiers:

| source | type | tier |
|---|---|---|
| `project_documentation` (chorus4ai.org) | documentation | 2 |
| `nih_reporter_project` | NIH project page | 4 |
| `cohort_2_webinar` | tutorial | 4 |
| `github_organization_overview` (captured 2025-11-14) | historical documentation | 5 |

**1. Released admission count — resolved.** The project website states a *Current
Released Dataset* of **50,000 patient admissions from ICU, PICU and NICU**; the
cohort 2 webinar states that *as of August 2025* the dataset covered 14 different
hospitals with **over 45K unique admissions**. `d4d download priority --project
CHORUS --decide project_documentation,cohort_2_webinar` returns
`project_documentation` (tier 2, stronger than every other source named). The
website figure is recorded in `instances[0].counts`, and
`instances[0].source_caveats` records that the sources disagreed, what each said,
and which was preferred.

**2. Anticipated final size — not a disagreement.** The website's *Anticipated
Final Dataset* of 100,000 patient admissions and the NIH RePORTER abstract's "more
than 100,000 critically ill patients" agree in magnitude and differ only in unit.
Neither is the released dataset, so neither is written into `instances[0].counts`;
both inform `updates.update_details` and `known_limitations[3]`.

**3. Award number notation — not a disagreement.** NIH RePORTER gives project
number `1OT2OD032701-01` with core project number `OT2OD032701`; the website gives
award number `OT2OD032701`. Two NIH notations for one award. `grant_number` holds
the full project number and `funders[0].grants[0].source_caveats` records both.

**4. Imaging volume — not comparable.** The website reports 7,642 admissions with
radiology data; the webinar reports 1000 images available as of August 2025. The
units differ (admissions, images) and so do the dates.
`distribution_formats[2].source_caveats` records this rather than choosing.

### Corrections made to the full record

| # | slot | correction |
|---|---|---|
| 1 | `distribution_formats[0].description` | Rewritten. It had asserted that nursing flowsheets specifically carry "a published OMOP schema with extensions". The webinar's data-type table is extracted with its column values interleaved, so no value can be assigned to a named row with confidence. The description now states only what the extraction sustains, and the reasoning is recorded in a new `distribution_formats[0].source_caveats`. The slot still holds a value. |
| 2 | `distribution_formats[1].description` | Rewritten to drop the clause "Access control metadata for this data type is listed as planned" — the same misattribution of a scrambled table cell. The slot still holds a value. |
| 3 | `distribution_formats[3].description` | Rewritten to drop the same "Planned" attribution. The slot still holds a value. |
| 4 | `distribution_formats[4].description` | Rewritten to drop the same "Planned" attribution. The slot still holds a value. |
| 5 | `source_caveats` (top level) | Added that `title` is the award and project title (the NIH page and the GitHub README state it in the same words), that the bundle gives the dataset no separate title and no DOI, and that this is why the project site is the record's identifier. |
| 6 | `creators[0..5].principal_investigator` | Structural, made during Phase 1 validation: the slot's induced range is a scalar reference, so a nested `Person` object fails validation. Each holds the person's name as the slot's own description prescribes, and the person's institution is in the sibling `affiliations`. |

Nothing was **back-ported**: the audit found no source-supported fact that the
full record omitted. Every value the audit changed is a removal or a restatement
of a claim already receipted from the chunk it came from, so no receipt entry
needed a new `{slot, snippet}` pair. `d4d receipts check --strict` was re-run
after the corrections and still reports 8/8 chunks, 109/109 snippets verified, no
findings.

### Shape and slot-filling audit

- No prose sits where the schema requires a list; no enum value outside its
  schema's permissible values (`conforms_to_standard` uses `OMOP_CDM`, `DICOM`,
  `WFDB` and `OTHER`, the last for EDF+/Persyst and OHNLP, which the enum does
  not name).
- No commentary is embedded inside a name, identifier or affiliation value. All
  evidence commentary sits in `source_caveats`, never in `notes`; the record
  populates `notes` nowhere.
- Structured slots are filled before prose: `funders[0].grants[0].grant_number`
  rather than the number inside a description, `creators[*].affiliations[*].name`
  rather than the institution inside prose, `instances[0].counts` as an integer.
- **No organization or person identifier is asserted.** The bundle contains no
  ROR, ORCID, DOI or ARK, and none is supplied from memory. `Organization`
  entries carry a name and no `id`, which the schema permits.

### Deliberate omissions

Recorded here because an absent slot is a claim about the evidence:
`collection_timeframes` (the bundle states no period the retrospective clinical
data covers; the award period is a funding fact and lives on the grant),
`known_biases` (the bundle describes bias *management*, which is in
`sampling_strategies` and `ethical_reviews`, and names no known bias present in
the data), `future_use_impacts`, `discouraged_uses`, `prohibited_uses`,
`retention_limit`, `version_access`, `errata`, `variables`, `anomalies`,
`participant_compensation` (the $8,000 figure in the bundle is a trainee stipend,
not participant compensation), `informed_consent`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `regulatory_restrictions` (HIPAA
and GDPR appear only as topics in the training curriculum), `ip_restrictions`,
`is_tabular`, `total_file_count`, `total_size_bytes`, `doi`, `version`,
`license` at dataset level, `publisher`, `citation`, and `related_datasets`.

## Phase 4 — re-derivation, checks and repair

```
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s .../data_sheets_schema_all.yaml      -C Dataset     <full>
poetry run linkml-validate -s .../data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <full> --target-class Dataset
poetry run linkml-term-validator validate-data <core> --target-class CoreDataset
poetry run d4d receipts check --label <LABEL> --project CHORUS --strict
poetry run d4d download scope --check --project CHORUS
grounding.check_run(full, core, bundle, uriorcurie_slots())
report_claims.check_report(report, full, core, declared_slots())
```

| check | result |
|---|---|
| Full schema validation | No issues found |
| Full term validation | Validation passed |
| Core schema validation | No issues found |
| Core term validation | Validation passed |
| Pair consistency | **PASS** — 79 schema-identical slots; projected `resources`; per-record exempt `conforms_to_class`, `conforms_to_schema` |
| Coverage receipt | chunks 8/8, snippets 109/109 verified, no findings |
| Grounding | `{'grounded': 0, 'minted_fragment': 0, 'absent': 0}` — no external identifier of any authority is stated, so none can be ungrounded |
| Scope | in scope; the record does not identify itself as a dataset the manifest declares distinct |
| Report claims | see below |

The pair checker emitted **no** `semantic-review-required` warning, because the
full record has no `file_collections` and the core therefore no `distributions`.
The unprompted reviews are performed and recorded below regardless — a missing
warning is not evidence that review was unnecessary.

No finding from any checker required a change to the **record**, so **there is no
`repair` phase and no `report_after_repair`**. The four Phase 3 corrections above
were made during the audit, before the Phase 4 checks ran, and the core was
re-derived from the corrected full record.

One finding did require a change to **this report**. Its first draft described the
four Phase 3 corrections with cells beginning "Removed …", and the report-claims
checker read each as a claim that the slot had been removed and returned four
`removal_not_performed` findings — correctly, because those slots were rewritten
and still hold values. The rows now say so. Re-run:
`{'checked': True, 'claims_checked': 0, 'claims_unnamed': 0}`, 0 findings.
`claims_checked` is 0 because this run removed no slot and the checker does not
yet read the `No slots were removed.` sentinel (#684); the sentinel is written
anyway so the count is measured the day it does.

## Claims

No slots were removed.

## Semantic review

| review | finding |
|---|---|
| `file_collections` ↔ `distributions` (the checker's only warning) | The checker emitted no warning: the full record declares no `file_collections`, so the core declares no `distributions`. The bundle describes data *types*, their standards and their volumes, never files, paths, counts or byte sizes, so the modality structure is carried by `distribution_formats` — whose `format` slot is documented for exactly this ("WFDB, OMOP CSV bundle") — and no file-level structure is invented. **reviewed: consistent** |
| `total_file_count` / `total_size_bytes` against the entries beneath them | Both absent, and correctly so: there are no `file_collections` to aggregate. The one volume figure the bundle gives — 23 Tb of waveform data — is a per-modality figure for one distribution and is not a dataset total, so it is stated in `distribution_formats[3].description` and not promoted to `total_size_bytes`. **reviewed: consistent** |
| `dialect` / `is_tabular` against the files | Both absent. `dialect` is derived only from `File` entries and there are none. `is_tabular` is deliberately omitted: the dataset is explicitly multimodal (DICOM imaging, WFDB and EDF+/Persyst waveforms, tokenized notes alongside OMOP tables), the bundle states no boolean, and asserting either value would be inference. **reviewed: consistent** |
| Historical release read as the current one | This is the live risk for CHoRUS, whose website states a current and an anticipated figure side by side and whose webinar states a third from August 2025. The record reads only the website's *Current Released Dataset* as current (`instances[0].counts: 50000`); the *Anticipated Final Dataset* of 100,000 admissions across 9 modalities is in `updates.update_details` and `known_limitations[3]`, framed as a target; and the webinar's August 2025 state — 45K admissions, 1000 images, EEG extraction in process — is dated in every place it appears (`instances[0].source_caveats`, `known_limitations[0]`, `known_limitations[1]`, `is_deidentified`). No future or superseded figure is stated as current. **reviewed: consistent** |
| Counts across the record | 14 contributing hospitals (all four sources), 20 institutions / 20 academic centers (website and GitHub), 60+ consortium members, 9 data modalities, 50,000 released and 100,000 anticipated admissions, 1.6 billion OMOP rows, 7,642 admissions with radiology data, 23 Tb of waveforms — each appears once in the slot that answers for it, with no figure restated in a second slot under a different framing. **reviewed: consistent** |
| Project label and dialect of the generated prose | The manifest's `naming:` block declares `canonical_label: CHoRUS`. Every sentence composed for this record uses it; the only occurrences of `CHORUS` are in the mandated header block and the bundle path, which are fixed text. Generated prose is American English throughout (`standardized`, `organization`, `analyzed`, `license`, `program`, `centers`); the two occurrences of `analyses` are the American plural of "analysis". Quoted source text keeps its source's spelling, including the website's "repoitory" and the GitHub description's "A Privacy Scan tools for medical records", both flagged in `source_caveats` rather than silently corrected. **reviewed: consistent** |
| License scope | The GitHub README's "This project is licensed under the MIT License" governs the organization's software repositories, not the clinical dataset, which every source describes as controlled access under a signed licensing agreement. MIT and Apache-2.0 are recorded on the `Software` entries that carry them; the dataset-level `license` slot is left absent and `license_and_use_terms.source_caveats` says why. **reviewed: corrected** — an earlier reading would have put MIT on the dataset. |
| Minted identifiers | Every minted id is a fragment on the record's own identifier `https://chorus4ai.org/`, which the manifest declares and the bundle attests. No fragment is hung on an organization identifier, and no prefix outside the schema's declared set is invented. Fragments are minted only for objects the schema requires an `id` on; nothing is labeled that the schema would have accepted without one. **reviewed: consistent** |

## Prompt condition

Condition: **generic-v6**, resolved prompt
`src/download/prompts/d4d_generic_arm_prompt_v6.md`, rendered for this project and
label and passed to the provenance recorder as `--prompt-text`. The instruction
carries no project-specific factual content, no quality warning and no outcome
expectation; the only project-varying fields are the mechanical ones (project
name, arm, method, bundle path, label, runtime, provider, model, output paths).

## Result

Both records validate against their schemas and their ontology terms, the pair
checker passes on the re-derived pair, the coverage receipt is complete and every
snippet verifies, no identifier in the record is ungrounded, and the record is in
scope. No discrepancy remained unresolved.
