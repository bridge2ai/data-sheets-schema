# CM4AI full/core reconciliation

Run label: `2026-07-23_gpt-5.6-sol-ultra-fast`

Runtime: Codex CLI; provider OpenAI; model `gpt-5.6-sol`; reasoning effort
`ultra`; mode `fast`; generated 2026-07-23.

## Phase 3 — source and provenance audit

### Evidence boundary and read history

The only factual inputs read were:

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- the `CM4AI` block in `data/preprocessed/source_manifest.yaml`
- after generation, the exact same-run full and core artifacts listed below

Structural and procedural inputs were the required repository instructions,
`D4D_Core.yaml`, the merged full/core LinkML schemas under
`src/data_sheets_schema/schema/`, and
`src/data_sheets_schema/d4d_pair_consistency.py`. Normal project configuration
was used only to run the validators.

No prior-run D4D full or core record, prior reconciliation report, evaluation
output, test-fixture fact, git history, web content, or model-memory CM4AI fact
was used. No content under `data/d4d_individual/` was read. No content under
`data/d4d_concatenated/` was read except the two exact same-run YAML paths after
they had been created.

### Source authority and scope findings

- The latest release is the June 2026 Beta release, DOI
  `10.18130/V3/HIGT4C`. The project page's displayed 17 June 2025 date conflicts
  with its June 2026 label; the manifest's curated official Dataverse metadata
  resolves publication to 17 June 2026 and records version-2 release time
  `2026-07-15T20:28:19Z`.
- HIGT4C has no file inventory in the allowed bundle. The exact selected
  inventory is the distinct October 2025 Beta release, DOI
  `10.18130/V3/K7TGEM`, displayed version 2.1/citation V2, with eight public ZIP
  archives. No K7TGEM count, size, format, or checksum was assigned to HIGT4C.
- March 2025 (`B35XWX`) and June 2025 (`F3TD5R`) were retained only in their
  manifest-authorized historical scopes. March has six public files and
  displayed version 1.4/citation V1. June has 21 public files and displayed
  version 2.1/citation V2; its capture exposes only the first ten, which were not
  represented as a complete inventory.
- March IF archives report 563 proteins, revised June/October IF archives
  report 464, and the current flagship page reports 523. These snapshot scopes
  were kept separate.
- Project-wide metrics (1,374 interactions, 53,788 IF images, 7,023 proteins,
  11,739 genes, and 21.4 TB) were not treated as release totals. In particular,
  21.4 TB was not converted into `total_size_bytes`.
- Public Dataverse files and embargoed external perturb-seq resources coexist;
  their access scopes were recorded separately.
- The peer-reviewed U2OS resource is distinct from the MDA-MB-468/KOLF2.1J
  release series. Its counts and demonstrated uses were explicitly scoped and
  were not merged into release counts.
- Dataset data, the bioRxiv preprint, the Nature article, and software have
  different licenses. Only the dataset's CC BY-NC-SA 4.0 terms were placed in
  dataset license slots.
- The selected October citation's 47 creators were retained in source order,
  including the source spelling `Ballllosero Navarro`. Trey Ideker's PI/contact
  roles, Jillian Parker's governance role, the two named ethical reviewers, the
  collaborating institutions, and NIH award identifiers were checked against
  their authoritative source scopes.

### Findings and corrections

- Phase 1 schema validation identified reference-shape errors: `Person` and
  `Grantor` fields without inline semantics were corrected from mappings to URI
  references, and four release-date values were quoted so YAML preserved the
  schema-required string type.
- The Phase 3 source audit found that a blanket
  `was_validated_verified: true` assertion across all five acquisition entries
  was broader than the sources support. It was removed from full first and then
  from core. Source-supported, method-specific QC and processing statements
  remain.
- Core-only distributions structured the source-supported filename-derived
  formats and exact MD5 values. Those facts were already present in the full
  `file_collections` descriptions, so no additional Phase 2 fact was missing
  from full and no other back-port was required.
- A read-only grouped consistency audit checked release identifiers and
  versions, resource and inventory counts, creator order, date types, licenses,
  access/inventory coverage, all 14 MD5s, format mappings, absent exact byte
  totals, and absence of cross-release leakage. All 20 grouped checks passed.

### Phase 3 validation

All commands exited 0:

```text
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d.yaml
Result: No issues found

poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
Result: Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d_core.yaml
Result: No issues found

poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
Result: Validation passed
```

Phase 3 unresolved source or within-record contradictions: **0**.

## Phase 4 — strict full/core reconciliation

### Schema-derived synchronization and identity

The pair validator was run exactly once with `--sync-core` after the Phase 3
audit:

```text
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d_core.yaml \
  --sync-core --json
```

Result: passed; **76 schema-derived identity slots**; projected slot
`resources`; zero errors. Synchronization added
`# Phase 4 reconciliation: completed` to the core header. The audited full
record was canonical for every schema-identical shared slot.

### Validator warning and semantic review

The validator reported one warning:

```text
semantic-review-required at $.file_collections <-> $.distributions:
deterministic matches=16, unmatched core distributions=[]
```

That warning and every related object were reviewed:

- All 16 full collections match exactly one core distribution by unique `id`;
  names, descriptions, paths, and stated compression agree. There are no
  unmatched or ambiguous objects.
- Eleven exact files map to `ZIP`, `application/zip`, and `zip`; three exact
  RO-Crate metadata paths map to `JSON` and `application/json`.
- Format and media type remain absent for the HIGT4C aggregate because its
  inventory is unavailable, and for the heterogeneous 21-file F3TD5R aggregate
  because one format would be false. Thus 14 distributions have exact formats
  and two are intentionally unspecified.
- All 14 source-provided MD5 checksums are identical between the full
  collection descriptions and core `md5` fields. No unsupported `hash` or
  `sha256` value was added.
- Displayed KB/MB/GB sizes are rounded. Consequently, no
  `FileCollection.total_bytes`, `CoreDistribution.bytes`, top-level
  `total_size_bytes`, or cross-version byte sum was invented.
- Exact direct datafile URLs are absent from the source capture and were not
  invented. Full collections retain their release DOI/page scope; shared
  `distribution_formats` carries the selected K7TGEM DOI and UVA Dataverse
  access URLs.
- Full resource file counts remain release-scoped: K7TGEM 8, F3TD5R 21, and
  B35XWX 6; HIGT4C has no count. The core schema has no corresponding total-file
  slot, so counts are not fabricated at distribution level.
- Five resources have equal `id` coverage. Every nested schema-identical value
  is deeply identical; full-only resource counts are omitted from the core
  projection as required.
- Top-level HIGT4C identity/version/access, historical version entries, release
  dates, CC BY-NC-SA terms, maintainers, people, organizations, modality facts,
  and limitation statements were reviewed wherever repeated. Their release,
  publication, project, and study scopes do not conflict.

The semantic review found **0 unresolved contradictions**.

### Independent pair check

The validator was then run without synchronization:

```text
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d_core.yaml \
  --json
```

Result: passed; 76 identity slots; projected `resources`; zero errors. The
single `semantic-review-required` marker repeated, with 16 deterministic
matches and no unmatched distributions, and is fully addressed above.

### Final validation

After synchronization and semantic review, the same four full/core schema and
term commands listed under Phase 3 were run again. All exited 0:

- full schema: `No issues found`
- full terms: `Validation passed`
- core schema: `No issues found`
- core terms: `Validation passed`

Final shared-slot status: every schema-identical value and presence state is
deeply identical. Final pair status: **passed**. Final unresolved
contradictions: **0**.

## Changed artifacts

Only these run artifacts were created or modified:

- `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_reconciliation.md`
