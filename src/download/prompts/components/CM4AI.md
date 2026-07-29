# CM4AI — GC-specific prompt components

## referent-pin

The subject of this record is the **CM4AI data-release programme, as an ongoing
quarterly release series** — not any single release and not a single modality.

Consequences to hold to:

- Individual releases (March 2025, June 2025, October 2025, June 2026) are
  `resources` of the programme.
- `file_collections` describes the **current** release. Populate it; the file
  inventory is part of what this record documents.
- Top-level `version`, `doi`, `issued` and `total_size_bytes` describe the
  programme, which has no single value for them. Leave them absent rather than
  taking the current release's values.

Rationale, so this is auditable rather than arbitrary: `Dataset` admits one
referent, and CM4AI decomposes three ways — programme, release, modality. The
evidence supports all three, so without a fixed choice replicates model
different things and the records are not comparable. Measured on 2026-07-28,
unpinned generic runs chose inconsistently (`d4d:CM4AI` twice, the programme
URI once) and emitted **zero** `file_collections`, where pinned runs emitted 10
in all three replicates.
