# Root-level D4D schema drafts, moved 2026-08-08 (#409)

Twelve `D4D_*.yaml` files that had accumulated in the **repository root**,
where no schema module belongs. Moved here rather than deleted: they were never
tracked in git, so until this commit they had no recovery path at all.

Following the precedent of `data/ATTIC/root_downloads/`, which holds legacy
directories moved off the repository root on 2024-12-19.

## What they are

Stale copies of the schema modules from **before classes were redistributed
between modules** — not an alternative design, and not the current modules.
Each shares its `id` and `name` with the live module of the same filename in
`src/data_sheets_schema/schema/`, but carries an older class inventory:

| file | this copy has | the live module has |
|---|---|---|
| `D4D_Minimal.yaml` | `Dataset`, `DatasetCollection`, `Information` | `MinimalDataset`, `MinimalDatasetCollection` — renamed to stop clashing with the main classes |
| `D4D_Collection.yaml` | 12 classes, incl. `EthicalReview`, `CollectionConsent`, `DataProtectionImpact`, `DatasetProperty` | 7 classes; those moved to `D4D_Ethics` and `D4D_Base_import` |
| `D4D_Ethics.yaml` | 6 classes, incl. `DirectCollection` | 5; `DirectCollection` moved into `D4D_Collection` |

Sharing an `id` with a live module is why they could not simply be left in
place: anything that imported one would collide with the real module.

## How they got there

Every file carries a UTF-8 BOM and CRLF line endings. Nothing in this
repository writes either — `gen-project` and LinkML emit LF without a BOM — so
they arrived from a Windows editor or a browser download rather than from any
tool here. They were referenced by nothing: the only occurrences of these
filenames in the tree are in `CLAUDE.md` and the agent definitions, and all of
those mean the modules under `src/data_sheets_schema/schema/`.

The bytes are unchanged by the move, BOM and CRLF included; md5s were compared
before and after.

## If you need one

They are superseded. The current modules are in
`src/data_sheets_schema/schema/`, and `make gen-project` regenerates everything
derived from them. Nothing in the build, the tests, or the documentation reads
this directory.
