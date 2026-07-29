# AI_READI — GC-specific prompt components

## fact

The input bundle contains records for **more than one release of the same
dataset**, and they disagree on headline figures:

- **v2.0.0** — FAIRhub `/datasets/2` and the v2 documentation. The FAIRhub page
  states plainly that this version is no longer accessible. Reports 2.01 TB
  across 165,051 files.
- **v3.0.0** — FAIRhub `/datasets/3`, DOI `10.60775/fairhub.3`, published
  2025-11-17, plus the v3 documentation and the FAIRhub API record. Reports
  3.82 TB across 356,343 files.

The v2 sources are retained in the corpus as the only surviving record of that
release; they are not the current state of the dataset. Where the two disagree,
`data/preprocessed/source_manifest.yaml` carries a `curation_note` on each entry
naming which supersedes which.

A third FAIRhub record, `/datasets/4`, is a separate 100-participant "Mini
Version" published for pipeline development. It is a distinct derivative
dataset, not a version of the flagship one, and is not in this bundle.

Rationale: without this, resolving the conflict is left to inference, and the
figures a record reports depend on which source a given replicate happened to
prefer.
