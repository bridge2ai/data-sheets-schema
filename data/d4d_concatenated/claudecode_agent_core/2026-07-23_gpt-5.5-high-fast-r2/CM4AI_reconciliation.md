# CM4AI Phase 3 Reconciliation

## Scope

Phase 3 reconciliation was limited to the already generated CM4AI full and core records:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d_core.yaml`
- Sources: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- Provenance: `data/preprocessed/source_manifest.yaml`

No unrelated project files were modified.

## Initial Validation

- Full Dataset validation: passed before reconciliation.
- CoreDataset validation: passed before reconciliation.

Commands:

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d.yaml
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d_core.yaml
```

## Overlap Checks

Compared shared top-level scalar fields present in both records:

- `id`
- `name`
- `title`
- `description`
- `doi`
- `page`
- `language`
- `license`
- `version`
- `download_url`
- `publisher`
- `issued`
- `created_on`
- `last_updated_on`
- `is_tabular`

After reconciliation, all shared top-level scalar fields are byte-equivalent after YAML parsing. Narrative overlap was also checked for the release-resource descriptions affected by this correction; both records now distinguish the HIGT4C current release from the retained DXWOS5 aggregate/project resource and the historical B35XWX, F3TD5R, and K7TGEM releases.

## Discrepancy

The generated records used `DXWOS5` as the top-level dataset DOI/id/download target and `2.1` as the top-level version. This conflicted with the current factual source bundle:

- `data/preprocessed/source_manifest.yaml` states that the CM4AI release page labels `HIGT4C` as the June 2026 release, and that verified Dataverse metadata reports publication date `2026-06-17` with version 2 release time `2026-07-15T20:28:19Z`.
- `data/preprocessed/concatenated/CM4AI_preprocessed.txt` records the CM4AI data-release page as "June 2026 Data Release (Beta)" with DOI `doi.org/10.18130/V3/HIGT4C`.
- The same source bundle retains historical Dataverse release/resource records for `B35XWX`, `F3TD5R`, `K7TGEM`, and the aggregate/project-level `DXWOS5` resource.

## Resolution

Top-level full and core fields were corrected consistently:

- `id`: `https://doi.org/10.18130/V3/HIGT4C`
- `doi`: `10.18130/V3/HIGT4C`
- `version`: `2`
- `download_url`: `https://doi.org/10.18130/V3/HIGT4C`
- `issued`: `2026-06-17T00:00:00Z`
- `created_on`: `2026-06-17T00:00:00Z`
- `last_updated_on`: `2026-07-15T20:28:19Z`

The core `status` field was updated to identify HIGT4C as the current/latest published beta release according to CM4AI release documentation and verified Dataverse metadata.

Resource sections were updated without dropping historical evidence:

- `DXWOS5` remains listed as an aggregate CM4AI Dataverse project resource.
- `B35XWX` remains the March 2025 Beta release V1.4 resource.
- `F3TD5R` remains the June 2025 Beta release V2.1 resource.
- `K7TGEM` remains the October 2025 Beta release V2.1 resource.
- `HIGT4C` is represented as the June 2026 Data Release (Beta), version 2.

The erroneous displayed page date `June 17, 2025` is retained only as a documented source-page discrepancy in descriptions, not as a normalized release date.

## Final Validation

- Full Dataset validation: passed after reconciliation.
- CoreDataset validation: passed after reconciliation.
- Remaining overlapping scalar conflicts: zero.

Commands:

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d.yaml
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d_core.yaml
```

Both returned `No issues found`.
