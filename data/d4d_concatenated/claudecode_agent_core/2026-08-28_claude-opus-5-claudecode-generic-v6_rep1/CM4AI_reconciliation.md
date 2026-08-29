# CM4AI reconciliation — 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1

Four-phase project agent, generic-v6 prompt, BASELINE arm (input documents
only). Runtime Claude Code, provider Anthropic, model claude-opus-5,
temperature 0.0.

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_coverage_receipt.yaml`
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
  (md5 `1dfd34e5610fed7c22bea1f09c0bc60c`, 7,866 lines, 28 chunks)

## Referent

`Dataset` admits one referent. The one chosen is the **CM4AI dataset as the
ongoing quarterly release programme**, identified by `https://cm4ai.org/`, which
is the `referent_id` the input manifest declares for this project. The
manifest's `referent_note` states that the Dataverse releases "are releases of
this dataset, not separate datasets", and the `retained_because` note on the
October 2025 source states that the pinned referent is "the release programme as
an ongoing quarterly series, with releases as `resources`". The record follows
that: five releases sit in `resources`, each identified by its own DOI CURIE,
each carrying its own version, publication date, description and file inventory.
The same choice is held in the core record, where `resources` is projected to
those five ids. `d4d download scope --check --project CM4AI` reports the record
in scope.

**One scope judgement was required and is recorded here.** The bundle's
highest-profile source is the Nature article "Multimodal cell maps as a
foundation for structural and functional genomics", which acknowledges the
Bridge2AI award that funds CM4AI. The map it reports was built in U2OS
osteosarcoma cells, which are not among the cell lines any CM4AI release covers
(MDA-MB-468 and KOLF2.1J), and its outputs are deposited at NDEx, MassIVE,
ProteomeXchange, ModelArchive and the Protein Complex Portal rather than in the
CM4AI Dataverse releases. It is therefore represented as an `external_resources`
entry naming those deposits, and its U2OS-specific figures — 5,147 proteins, 275
assemblies, 111 heterodimeric structures, 772 pediatric tumors — are **not**
carried into this dataset's `instances`, `subsets` or composition slots. Where
the project preprint independently attests the same method as CM4AI's own
(the MuSIC pipeline, node2vec embedding, contrastive co-embedding, community
detection, integrative structure modeling, LLM assembly naming), the method
slots are populated and cite the preprint; the Nature article's study-specific
protocol detail stays inside the external resource. The Nature acknowledgement's
further funders are recorded in `funders[0].source_caveats` rather than as
funders of this dataset.

## Phase 1 — full record from the input documents

Read under the receipt protocol: the chunk manifest
`data/preprocessed/chunks/CM4AI_chunks.yaml` was confirmed `current` before
reading, then all 28 chunks were read in manifest order with the file-reading
tool, each chunk's receipt entry written before the next chunk was opened.

Final receipt state: **chunks 28/28 reviewed, snippets 367/367 verified, no
findings**. Of the 28 chunks, 19 are `extracted`, 3 are `redundant_with`
(c021, c024, c027 — the repeated Citation Metadata tails of the June 2025,
October 2025 and June 2026 releases) and 6 are `nothing_relevant` (the
concatenation preamble, the two bibliographies, Nature site chrome, and three
tails of Dataverse interface text).

Slot paths in the receipt were reconciled against the record as it was written,
so that every `{slot, snippet}` pair names a slot the record actually fills.
Nine snippets were corrected during that pass: one typo, and eight that a read
window had attributed to a neighbouring chunk (`snippet_adjacent_chunk`), which
were moved to the chunk that actually contains them.

`slots N/M with a receipt` is reported at 245 of 753 and is not gated. The
unreceipted remainder is dominated by the repeated structural keys of the 51
`File` and `FileCollection` objects (`format`, `media_type`, `compression`,
`file_type`, `collection_type`), which are shape derived from the schema's
enums rather than facts transcribed from a passage.

## Phase 2 — core derived by projection

`d4d derive core` was run on the validated Phase 1 file; no model judgement was
involved. The command reported:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml",
          "md5": "de489d720605a86dd22b4c24ec2dc26d"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

`distributions` is empty in the core, and that is correct rather than a gap: the
derivation builds `distributions` from **top-level** `file_collections`, and
this record has none. The file inventories belong to the individual releases,
which are `resources`, so they live on those resource objects where the evidence
puts them. How the dataset is obtained is carried instead by
`distribution_formats`, which the core keeps in full — the Dataverse landing
pages, the Data Access API endpoint, and the RO-Crate packaging.

## Phase 3 — source and provenance audit

Schema and term validation were re-run for the full record before the audit and
passed. No prior generated D4D record was read at any point: the only factual
inputs opened in this run were the declared bundle, `source_manifest.yaml`, the
chunk manifest, and the full and core schema files. No file under
`data/d4d_concatenated/` other than this run's own three outputs was read, and
no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was read.

### Source disagreements resolved by the manifest's ranking

The manifest ranks sources by `source_priority`, lowest tier strongest. Four
disagreements were found and each is recorded in a `source_caveats` on the slot
it affects.

| Disagreement | Sources and tiers | Resolution |
|---|---|---|
| Publication date of the current release | `data_release_documentation` (tier 2) displays "Released on: June 17, 2025"; `june_2026_dataverse_release` (tier 1) gives Publication Date 2026-06-17 | Tier 1 preferred. `resources[4].issued` and `distribution_dates[0].release_dates` state 2026-06-17; the caveat records both figures and notes that the release's own files are published in 2026, not 2025 |
| Number of institutions in the collaboration | `data_release_documentation` (tier 2) lists nine including UT Austin; `march_2025_dataverse_release` (tier 5) lists eight, omitting it | Tier 2 preferred; `creators[4].affiliations` lists nine. The caveat records the shorter list and notes the preprint independently gives UT Austin as an author affiliation |
| Version of the March 2025 release | Within one source: the page heading says "Version 1.4", the data citation on the same page ends "V1" | The ranking cannot decide within a single source; the finer-grained value is stated and the caveat records both |
| End of the project | `october_2025`/`june_2026_dataverse_release` (tier 1) say "through the end of the project in November 2026"; `nih_reporter_project` (tier 4) gives Project end 2026-08-31 | Not treated as a conflict: one is a planned end of data augmentation, the other an award end date. Both are stated in their own slots and the caveat says so |

Two further figure spreads are represented rather than resolved, because they
describe different releases rather than contradicting each other on one:

- **Imaging protein counts** — 563 (March 2025), 464 (June 2025 onward), 523
  (project summary page). Each is stated on the release it belongs to; no single
  figure is asserted for the dataset as a whole. `instances[3].source_caveats`
  records all three.
- **Data volume** — the project summary states 21.4 TB, while the displayed file
  sizes across the Dataverse releases total tens of gigabytes. The release
  records state that raw sequencing and raw mass spectrometry data are held in
  external repositories, so the two figures do not describe the same holdings.
  Neither is asserted as a total for the other; the top-level `source_caveats`
  records the gap and `total_size_bytes` is left absent.

### Back-ports into the full record

Three source-supported values were added, each with its receipt added to the
existing entry of the chunk the passage sits in:

1. `sampling_strategies[0]` — the dataset is a targeted sample of the proteome
   (100 chromatin modifiers and 100 metabolic enzymes selected by disease
   relevance; a further 500 imaging targets held pending earlier results; the
   CRISPRi atlas the genome-scale exception at 11,739 genes). Receipted to
   c010, c011 and c018. The slot had been overlooked in Phase 1 even though the
   evidence for it is explicit and it is what `known_biases[0]` implicitly
   depends on.
2. `resources[4].last_updated_on` — 2026-07-15, the publication date the June
   2026 release's image archives carry. Receipted to c026.
3. `license_and_use_terms` restructured — the repository's community norms and
   the Bridge2AI Code of Conduct were moved out of `notes` and into
   `license_terms`, where they belong as terms of use. The record now uses no
   `notes` slot anywhere; evidence commentary is in `source_caveats` throughout.

### Shape audit

- No prose sits in a slot the schema declares as a list; `ip_restrictions.restrictions`,
  `data_governance.stewardship_roles`, `keywords` and the `examples` lists each
  carry one statement per entry.
- No enum value outside the schema's declared permissible values is used;
  `linkml-term-validator` passes.
- No commentary is embedded inside a name, identifier or affiliation value.
- Identifier form: `doi` slots carry bare DOIs; `download_url` and `access_urls`
  carry URLs, as their `uri` range requires; `publisher`, organization ids and
  `data_governance.accountable_organization.id` carry the `ROR:` CURIE for the
  one ROR the bundle supplies. The three `data_topic` values are full IRIs
  because the schema declares no prefix for GO, NCIT or EFO, and the rule
  forbids inventing one.
- People: `principal_investigator`, `contact_person` and `committee_contact` are
  scalar references, so each holds the referenced Person's identifier — an
  `ORCID:` CURIE where the bundle supplies an ORCID, and a `mailto:` URI for
  Jillian Parker, for whom it supplies an email but no ORCID. Names sit in the
  containing object's `description`, and the one Person the sources name as a
  committee member is carried in full in the inlined
  `data_governance.committee_members`.

  **The form check counts `mailto` as an undeclared prefix, twice, and that is
  a deliberate choice rather than an oversight.** `Person` declares `id` as
  required, so the governance contact cannot be recorded without one. The rule
  forbids hanging a person off an organization's identifier, which rules out a
  fragment, and it directs that where no fragment is possible either, a
  resolvable URL is the better answer; `mailto:` is a registered URI scheme, not
  an invented CURIE prefix, and the address it carries is stated verbatim in the
  bundle. The alternative considered and rejected was to reuse the ORCID of
  "Parker J (University of California, San Diego)", who appears in the author
  roster of the same release records: the identification with "Jillian Parker
  (jillianparker@health.ucsd.edu)" is very likely correct, but no source in the
  bundle makes it, so asserting the ORCID would be an inference of exactly the
  kind the identifier rule prohibits.

## Phase 4 — re-derivation, checks, repair

The core was re-derived from the corrected full record with `--phase4-complete`.
`--sync-core` was not used and was not needed.

| Check | Result |
|---|---|
| `linkml-validate` full, class `Dataset` | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core, class `CoreDataset` | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` | PASS — 79 schema-identical slots; projected `resources`; exempt `conforms_to_class`, `conforms_to_schema` |
| `grounding.check_run` | `{'grounded': 6, 'minted_fragment': 51, 'absent': 0}` |
| `d4d receipts check --strict` | chunks 28/28 reviewed, snippets 367/367 verified, no findings |
| `d4d download scope --check` | in scope |
| `form` check (recorded by `d4d provenance record`) | british spellings 0, organisational fragments 0, GC label variants 0; undeclared prefixes `{mailto: 2}`, explained under the shape audit above |
| `d4d runs check --strict` | exit 0 |
| `d4d runs validate` | 1 valid, 0 invalid |

The provenance record is `record_mode: live` and carries all five phases
(`generate_full`, `derive_core`, `source_audit`, `reconcile`, `report`),
`inputs.receipt_expected: true`, and an `inputs.chunks` block naming the chunk
manifest for the exact bundle md5 this run hashed. It records two fields as
`unverified`: `model.temperature`, because the Claude Code runtime does not
expose a temperature setting to the agent or the recorder, so the header's 0.0
restates the prompt template rather than a measured parameter; and
`model.reasoning_effort`, which is absent because the route exposes no effort
ladder and this run named none. No per-phase `observed` block is recorded, as
the playbook directs for four-phase project-agent mode, where one subagent runs
all phases and there is no per-phase boundary to observe. No reasoning log
exists for this path (`runtime_cannot_capture`).

`d4d runs check --strict` reports one warning against this run, shared with the
sibling v6 records: *"unverifiable: request hash recorded without the spec that
produced it"*. The instruction as sent was recorded from the rendered
instruction file it was sent as, rather than from a render spec, so its hash is
recorded but cannot be re-derived by the render gate. The prompt file
`src/download/prompts/d4d_generic_arm_prompt_v6.md` is recorded as an input; the
check reports no `uncanonical` and no `missing` finding for this run, and the
strict check exits 0.

**Zero identifiers are absent from the bundle.** The 51 minted fragments are all
`FileCollection` and `File` ids, each hung off the attested DOI CURIE of the
release the file belongs to (for example
`doi:10.18130/V3/HIGT4C#cm4ai_apms_MDA-MB-468_paclitaxel.zip`). Both classes
declare `id` as required, and each fragment is pointed at by the containing
collection's membership, so these are labels the record uses rather than
identifiers nothing refers to. No fragment is minted for a person or for a part
that is only described.

## Claims

No slots were removed.

The one deletion made in Phase 4 was of values, not of a slot: `created_on` was
removed from all four release resources. The repository records the same Data
Creation Date of 2025-02-27 on every release, including the June 2026 release
whose own files are published in June and July 2026, so the field is a repeated
repository value rather than a per-release fact. It is now stated as such in the
top-level `source_caveats` and no creation date is asserted for any release.

## Semantic review

The pair checker emitted **no** `semantic-review-required` warning, because the
record has no top-level `file_collections` and therefore no derived
`distributions` for the checker to pair. The unprompted reviews Phase 4 step 1
names were performed regardless and are recorded here.

| Review | Finding | Outcome |
|---|---|---|
| `total_file_count` against the `file_count` values beneath it | March 2025: 6 = 1+1+3+1 ✓. October 2025: 8 = 2+2+1+3 ✓. June 2026: 10 = 2+2+2+1+3 ✓. June 2025: `total_file_count` is 21 but the enumerated collections sum to 10, because the capture of that release lists only its first ten files | **reviewed: corrected** — the release's own reported total is kept, and `resources[2].source_caveats` was rewritten to say explicitly that it is deliberately larger than the sum beneath it and why |
| `total_size_bytes` against the file entries | Absent at every level, and `bytes` is absent on all 51 File entries. The Dataverse pages display rounded sizes ("3.8 GB", "1000.1 KB") which cannot be converted to a byte count without fabricating precision; each displayed size is stated verbatim in the File's `description` instead | **reviewed: consistent** — no size total is asserted, so none can contradict the entries |
| `dialect` against the files | No File carries a `dialect`, so the derivation correctly omitted `dialect` from the core. The files are ZIP archives, JSON and HTML documents, and no source states a format dialect for any of them | **reviewed: consistent** |
| `is_tabular` against the files | Absent. The inventory is ZIP archives, JSON metadata and HTML documents; no source characterizes the data as tabular, and asserting `false` would be an inference | **reviewed: consistent** — omission is the correct answer here |
| A historical release read as the current one | The referent is the release programme, so all five releases are enumerated with their own versions and dates, and the current one is named by `version_access.latest_version_doi`. Two specific risks were checked: the March 2025 imaging count of 563 proteins being read as current (separated from the 464 of later releases in `instances[3].source_caveats`), and the identically named image archives across the June 2025, October 2025 and June 2026 releases (the June 2026 archives carry different checksums, which the Images collection description states) | **reviewed: corrected** — the repeated Data Creation Date of 2025-02-27 was found being carried onto the June 2026 release, where it would have asserted a stale creation date for data published in 2026; it was removed from all four releases and replaced by a caveat |
| Project-name usage against the manifest's `naming:` block | The manifest declares `canonical_label: CM4AI`. Composed prose uses "CM4AI" throughout. The formal name "Cell Maps for Artificial Intelligence" appears in `title`, in release names and in the grant name "Bridge2AI: Cell Maps for AI (CM4AI) Data Generation Project" — all proper nouns as their sources state them, which the naming rule exempts | **reviewed: consistent** |
| American English in composed prose | Swept for `analys-`, `organis-`, `licence`, `programme`, `modelling`, `characteris-`, `behaviour`, `centre`, `labelling`. The only hits are inside verbatim snippets in the coverage receipt (`Integrative Modelling Platform`, `licence` in the CC deed), which keep their source spelling, and the word "Analyses", which is American | **reviewed: consistent** |

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_coverage_receipt.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_reconciliation.md`

## Commands

```bash
poetry run d4d bundle chunk --check --project CM4AI
poetry run d4d download scope --project CM4AI
poetry run d4d download priority --project CM4AI

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 --project CM4AI --strict

poetry run d4d derive core \
  --full data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml \
  --out  data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d_core.yaml \
  --phase4-complete

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d_core.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run d4d download scope --check --project CM4AI
poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
poetry run d4d runs validate --project CM4AI --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1
```

## Final results

| Metric | Full | Core |
|---|---|---|
| Top-level slots populated | 53 | 50 |
| Populated keys, all nesting levels | 837 | 705 |
| Line count (informational only, not a quality gate) | 1,692 | 1,264 |
| Schema validation | pass | pass |
| Ontology term validation | pass | pass |

Releases enumerated as `resources`: 5 (`doi:10.18130/V3/DXWOS5`,
`doi:10.18130/V3/B35XWX`, `doi:10.18130/V3/F3TD5R`, `doi:10.18130/V3/K7TGEM`,
`doi:10.18130/V3/HIGT4C`). File entries with checksums: 51 across 17 file
collections.
