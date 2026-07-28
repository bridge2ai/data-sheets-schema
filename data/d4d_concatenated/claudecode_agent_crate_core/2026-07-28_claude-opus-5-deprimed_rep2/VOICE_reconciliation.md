# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep2

| | |
|---|---|
| Project | VOICE |
| Version label | `2026-07-28_claude-opus-5-deprimed_rep2` |
| Arm | DE NOVO WITH CRATE (documents + RO-Crate evidence) |
| Mode | Four-phase project agent, de-primed |
| Runtime / provider / model | Claude Code / Anthropic / `claude-opus-5[1m]` |
| Temperature | 0.0 |
| Input bundle | `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` |
| Source manifest | `data/preprocessed/source_manifest.yaml` |
| Crate manifest | `data/ro-crate_packages/crate_manifest.yaml` |
| Full record | `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml` |

---

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs used, in full:

- `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` (15,719 lines; 11 documents plus
  `VOICE_crate_metadata_reduced.json` and `ai_ready_score.json`)
- `data/preprocessed/source_manifest.yaml` and `data/ro-crate_packages/crate_manifest.yaml`
  (consulted for provenance scoping only, not for dataset facts)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`) and
  `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md` (method, not evidence)

No prior full or core D4D record was read, opened, grepped or consulted, from any arm, label or
date. Nothing under `data/d4d_concatenated/` was read other than the two outputs written by this
run. No `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was read.
No evaluation report, test fixture or schema example supplied a factual value. No live web content
was fetched.

Structure was derived at runtime from the schemas via `SchemaView` (`Dataset` and `CoreDataset`
induced slots, ranges, cardinality, inlining and enums). Reference-versus-inlined behaviour was
probed against the schema rather than assumed: `principal_investigator`, `grantor`,
`contact_person`, `reviewing_organization` and `governance_committee_contact` are identifier
references (strings), while `affiliations`, `grants`, `sampling_strategies` and
`missing_information` are inlined objects.

### Cross-source resolution

The bundle mixes documents of different dates and scopes with crate evidence describing one
specific release. Disagreements were resolved by scope and recency, and both sides were retained
with explicit attribution rather than silently collapsed.

| Topic | Sources | Resolution |
|---|---|---|
| Current adult release | `physionet_3_0_0` (v3.0.0, superseded); `physionet_3_1_0` (v3.1.0, current); crate (v3.0.0) | Both releases modelled as separate `resources`. v3.1.0 is current; v3.0.0 carries the crate-derived file inventory. `related_datasets` records `is_new_version_of`. |
| Adult vs pediatric | docs, `physionet_3_1_0`, `physionet_pediatric_1_1_0` | Kept as distinct cohorts under separate protocols and sites, never merged. No combined participant or recording count is asserted anywhere. `related_datasets` uses `is_supplemented_by`, not `is_version_of`. |
| Participant count | 833 (v3.0.0 and v3.1.0, docs); 306 (v1.0); 300 (pediatric) | `instances` carries 833 adult and 300 pediatric as separate instances; 306 retained only inside an explicit "earlier v1.0 release" clause. |
| Recording count | docs "~61,937 voice-derived recordings" for v3.0; PhysioNet per-feature counts (29,020–32,236 for v3.0.0; 28,640–32,522 for v3.1.0) | Both retained with attribution; the per-feature counts are recorded on the release resources, the docs aggregate on the recording instance. Not treated as a contradiction because they count different things. |
| Award number | `OT2OD032720`; `3OT2OD032720-01S3`; `3OT2OD032720-01S1`; `1OT2OD032720-01`; `3Tf-OTOD03272001S2`; `3TF-OT2ActfOD032720Projectf01S1` | Four clean renderings recorded as separate `Grant` objects with their source scope; the two garbled docs/crate renderings are quoted in the `FundingMechanism` description rather than promoted to `grant_number`. |
| Hosting / distribution platform | docs: Health Data Nexus; PhysioNet pages: PhysioNet + Synapse | Health Data Nexus statements explicitly scoped to the v1.0 release throughout; current releases attributed to PhysioNet, raw audio to Synapse. |
| IRB number 004890 | feasibility publication | Scoped explicitly to the app feasibility study, not to the data acquisition protocol. The crate records `irbProtocolId` as an empty string; no protocol ID is asserted. |
| Copyright | docs footer "© 2025 B2AI Voice"; crate "© 2026 University of South Florida" | Both quoted verbatim with their source, in `license_and_use_terms.license_terms`. |

### Corrections applied to the full record (then re-projected into core)

1. **`language` scope.** The original wording generalised "English was the only language option"
   across all releases. The documentation makes that claim specifically about v2.0.0. Rewritten to
   quote the v2.0.0-scoped statement and to add the adult exclusion criterion, the February 2025
   IRB update adding Spanish-language collection, and the pediatric English-proficiency
   requirement.
2. **`total_file_count` removed from the adult v3.0.0 resource.** The value 15 was the count of
   RO-Crate dataset entities, not files: four of the fifteen are grouped entities covering a
   directory of TSV and JSON files. The entity count, the checksum coverage (11 of 15) and the
   grouping caveat were moved into the resource description, where they are accurate.
3. **Enrollment targets added to `updates.update_details`.** The sources state four different
   targets at different dates and scopes, and none was represented: 10,000 by 2027 (documentation);
   30,000 human voices (audiomics viewpoint); 30,000 overall with 5,000 at USF and up to 5,000 per
   disease category (IRB protocol); ~3,000 by November 2026 (crate `rai:dataCollectionTimeframe`).
   All four are now recorded with their source.
4. **HIPAA scope clarified in `regulatory_restrictions.other_compliance`.** The documentation
   answers "Yes" to applying HIPAA de-identification rules to the released dataset, while the Data
   Transfer and Use Agreement states the transferred data is PII under OMB M-07-16 and "not covered
   under HIPAA". Added an explicit statement that these address the released de-identified product
   and the transfer instrument respectively, so `hipaa_compliant: compliant` is not read as
   contradicting the DTUA.

### Unsupported, stale or mis-scoped assertions found: none remaining

Every populated slot traces to a quoted or paraphrased statement in the declared bundle. Values the
bundle does not support were left absent rather than inferred — notably `total_size_bytes` (the
crate states "12.9 GB" without a unit basis, so it is retained as text and not converted to an
integer byte count), `Instance.data_topic` and `Instance.data_substrate` (no ontology terms in the
bundle), `compression` (never asserted), and `orcid`/`email` for most people (the preprocessed
documentation renders most addresses as redacted placeholders, so only the addresses that appear
literally — `yaelbensoussan@usf.edu`, `DACO@b2ai-voice.org`, `RSCH-IRB@usf.edu` — were used).

### Internal consistency within each file

Repeated identifiers, versions, dates, counts, licences, access rules, people and organisations
were checked for internal agreement in each file independently: 833 participants (v3.0.0, v3.1.0,
adult instance), 300 pediatric participants, five North American sites, DOIs `10.13026/k81f-qr68`,
`10.13026/8xbn-nq66`, `10.13026/h995-bt35`, `10.13026/249v-w155`, `10.13026/37yb-1t42`,
`10.13026/mf9s-5r03`, `10.57764/qb6h-em84`, the release dates, the Registered Access
License/Agreement pairing, and the DACO contact route all agree wherever repeated. No internal
contradiction was found in either file.

### Facts discovered during Phase 2

None. Core was produced by schema-driven projection of the audited full record plus two core-only
slots derived from the same bundle, so no Phase-2 discovery required back-porting.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Shared slots were computed at runtime from `SchemaView`, not from a hand-written list.
`Dataset` ∩ `CoreDataset` yields the shared set; the deterministic validator resolved
**76 schema-identical slots** plus one projected slot.

- Full-only slots in `Dataset`, correctly absent from core: `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`, `splits`,
  `subsets`, `third_party_sharing`, `variables` — 13 populated full slots dropped.
- Core-only slots in `CoreDataset`: `distributions`, `dialect`.
- `resources` is the projected slot: range `Dataset` in full, `CoreDataset` in core.

Every schema-identical slot is present in both records or absent from both, and its parsed YAML
value is deeply identical including nested mapping values and list order. Narrative fields were
copied verbatim — nothing was condensed, paraphrased, reordered or omitted to make core shorter.

### Projection: `resources`

Six resources, matched by `id`, equal coverage in both records:

| `id` | scope |
|---|---|
| `https://doi.org/10.13026/8xbn-nq66` | adult v3.1.0 (current) |
| `https://doi.org/10.13026/k81f-qr68` | adult v3.0.0 (crate-described) |
| `https://doi.org/10.13026/h995-bt35` | pediatric v1.1.0 |
| `https://www.synapse.org/Synapse:syn72370534/` | adult raw audio, controlled access |
| `https://www.synapse.org/Synapse:syn73617068` | pediatric raw audio, controlled access |
| `https://doi.org/10.57764/qb6h-em84` | Health Data Nexus v1.0 |

Every nested schema-identical slot is deeply identical across the pair. The one full-only nested
slot, `file_collections` on the v3.0.0 resource, is omitted from the core projection and re-expressed
as `distributions`, as the schema requires.

### Related, non-identical representations — semantic review

**`file_collections` → `distributions`.** 15 full file collections map one-to-one to 15 core
distributions on the same v3.0.0 resource. Names, descriptions and paths are byte-identical.
Checksums: `CoreDistribution.sha256` carries the eleven sha256 values the RO-Crate records; the same
eleven values also appear in the shared description text, and the four grouped entities
(diagnosis, enrollment, questionnaire, task) carry no checksum in either record, matching the crate.
Byte counts: `total_bytes: 1924570748` (full, `ppgs.parquet`) equals `bytes: 1924570748` (core); the
crate records no size for the other fourteen entities and neither record invents one. Formats:
`format: TSV` and `media_type: text/tab-separated-values` are set on `confounders.tsv` and
`demographics.tsv`, matching the crate's `format` field for those entities; the nine Parquet
distributions carry no `format`/`media_type` because `FormatEnum` and `MediaTypeEnum` have no
Parquet member, and mapping Parquet onto an unrelated enum value would be a fabrication.
Compression: unasserted on both sides — the sources state none. Access URLs and release scope:
both sides nest under the same v3.0.0 resource carrying `version: 3.0.0`,
`download_url: https://physionet.org/content/b2ai-voice/3.0.0/` and
`issued: 2025-12-16T00:00:00Z`. No conflict.

**`total_file_count` / `total_size_bytes` versus distribution-level values.** Neither is asserted in
either record after the Phase 3 correction, so there is no scope mismatch to reconcile. The crate's
"12.9 GB" content size and the eleven per-file checksums are recorded as text on the v3.0.0
resource in both records.

**`dialect`, formats and `is_tabular`.** `dialect` (`delimiter: "\t"`, `header: "true"`) is core-only
and is asserted solely on the v3.0.0 resource, derived from the documented read pattern
`pd.read_csv("demographics.tsv", sep="\t", header=0)`. `is_tabular: false` is asserted identically in
both records at top level and on the v3.1.0, v3.0.0 and pediatric resources, because each release
mixes dense Parquet tensors with TSV tables. The two agree: `dialect` describes the tabular phenotype
component, `is_tabular` characterises the release as a whole. The only `format` values asserted are
`TSV` on the two TSV distributions, consistent with both.

**Top-level identity, version and access versus resources, version history and distributions.**
The top-level `id` is the umbrella project resource and deliberately carries no `version`, `doi`,
`download_url` or `issued`, so it cannot conflict with the per-release values. The top-level
`license` names the Bridge2AI Voice Registered Access License for both adult and pediatric releases;
the v3.0.0 resource carries the version-specific licence URL from the crate — the same licence,
identified two ways. `version_access.versions_available` enumerates adult v1.1, v2.0.0, v2.0.1,
v3.0.0, v3.1.0, pediatric v1.0.0, v1.1.0 and Health Data Nexus v1.0; the release dates in
`distribution_dates` agree with that list, and every `download_url` on a resource also appears in
`distribution_formats.access_urls`. Adult v2.0.0 and v2.0.1 appear in the version history without a
corresponding resource: that is history coverage, not a contradiction. `latest_version_doi` at top
level is the adult concept DOI `10.13026/37yb-1t42`; the pediatric concept DOI `10.13026/mf9s-5r03`
is carried on the pediatric resource's own `version_access`, keeping the two projects' concept DOIs
scoped to their own projects.

**Historical versus current releases.** v3.0.0 versus v3.1.0, pediatric v1.0.0 versus v1.1.0, Health
Data Nexus v1.0, and the documentation statements that are explicitly about v2.0.0 are each labelled
with the version they describe, so their differing values are treated as release history rather than
as contradictions.

### Unresolved contradictions

None, within either record or between the two.

### Representation notes

- `issued` has range `datetime` in both schemas, but every publication date in the sources is a
  calendar date. Dates are encoded as `YYYY-MM-DDT00:00:00Z`; the midnight-UTC component is a
  schema-imposed encoding, not a source assertion.
- Identifiers for `Person`, `Organization` and `Grant` objects are required by the schema but not
  supplied by the sources. Locally-scoped CURIEs (`b2ai.voice.org:*`, `b2ai.voice.grant:*`) and
  fragment identifiers under the release DOIs were minted for structural purposes only; they carry
  no factual claim.

---

## Commands run

```bash
# Phase 1 / Phase 3 — full record
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 — core record
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — schema-derived pair consistency
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml

# Provenance record
poetry run d4d provenance record --project VOICE --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-deprimed_rep2 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt
```

`--sync-core` was run against a scratch copy only, to confirm it would be a no-op; parsed content was
identical before and after, so the committed core file was never rewritten by the synchroniser. Core
was produced by schema-driven projection of the audited full record, so synchronisation had nothing
to correct.

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d.yaml` (created; four Phase 3 corrections applied)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_d4d_core.yaml` (created; regenerated after the Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-deprimed_rep2/VOICE_provenance.yaml` (live provenance record)

## Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | PASS |
| Full — ontology term validation | PASS |
| Core — LinkML schema validation (`CoreDataset`) | PASS |
| Core — ontology term validation | PASS |
| Schema-derived pair consistency | PASS — 76 schema-identical slots, projected slots `['resources']` |
| Unresolved contradictions | none |
| Prior-run D4D read or cited | none |

Informational metadata (not a quality gate): full 77 populated top-level slots / 727 populated slot
instances including nested objects / 2,609 lines; core 64 populated top-level slots / 589 populated
slot instances / 2,020 lines.
