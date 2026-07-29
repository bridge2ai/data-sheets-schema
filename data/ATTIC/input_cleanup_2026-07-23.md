# Input cleanup and historical-content audit: 2026-07-23

## Active inventory

The active D4D input inventory is defined by
`data/preprocessed/source_manifest.yaml`. It contains 26 unique URLs selected
from the Bridge2AI GC Input Documents sheet and three curated historical
supplements whose unique content remains relevant:

| GC | Sheet sources | Historical supplements | Active total |
| --- | ---: | ---: | ---: |
| AI_READI | 7 | 0 | 7 |
| CHORUS | 3 | 1 | 4 |
| CM4AI | 7 | 2 | 9 |
| VOICE | 9 | 0 | 9 |
| **Total** | **26** | **3** | **29** |

The supplements are:

- CHORUS GitHub organization overview captured 2025-11-14.
- CM4AI March 2025 Dataverse release, DOI `10.18130/V3/B35XWX`.
- CM4AI June 2025 Dataverse release, DOI `10.18130/V3/F3TD5R`.

## Cleanup

No source files were deleted. Files not selected by the manifest were copied or
moved to:

- `data/ATTIC/raw/superseded_2026-07-23/`: 47 raw artifacts.
- `data/ATTIC/preprocessed/superseded_2026-07-23/`: 34 processed artifacts.
- `data/ATTIC/preprocessed/legacy_d4d_concatenations_2025-11-17/`: four
  generated GPT-5 D4D YAML bundles that had been misclassified as source
  concatenations.

The archived sets include duplicate downloads, failed NIH RePORTER JavaScript
stubs, Google Docs shell pages, superseded row-number variants, mixed-format
processed files, and sources no longer selected by the current sheet.

The 2026-07-23 refresh downloaded 24 canonical sources. The current PMC and
Nature endpoints for two AI_READI publications returned HTML instead of PDF, so
the existing validated PDF copies were retained:

- `AI_READI/bmjopen-2024-097449_row2.pdf`
- `AI_READI/s42255-024-01165-x_row3.pdf`

Both retained files have valid PDF signatures and produced non-stub text.

## Historical comparison

The audit compared the active corpus with the pre-cleanup 56-file processed
tree, archived downloads, and repository snapshots from 2025-11-14,
2025-11-17, 2025-11-21, 2025-12-19, and 2026-04-10. Historical physical-file
counts are not source counts: they include repeated row captures, format
variants, and failed downloads.

| GC | Pre-cleanup physical files | Active files | Missed distinct documents |
| --- | ---: | ---: | --- |
| AI_READI | 18 | 7 | None |
| CHORUS | 10 | 4 | GitHub organization overview; restored |
| CM4AI | 11 | 9 | March and June 2025 Dataverse releases; restored |
| VOICE | 17 | 9 | None |

### AI_READI

No distinct document was lost. The archived files resolve to:

- an older version of the current documentation page;
- four 107-byte FAIRhub pointers to the same dataset now represented by a
  complete FAIRhub extraction;
- two DOI-only pointers to current publications;
- Google Docs shells replaced by the complete Drive export;
- a duplicate BMJ article extraction;
- an older NIH RePORTER rendering of the same award; and
- a Zenodo PDF that had been misclassified as text.

The old license DOI pointer did preserve
`https://doi.org/10.5281/zenodo.10642459`; that identifier is now explicit as
the license source's `verification_url` in the manifest.

### CHORUS

The GitHub organization overview was a real omission. The current CHORUS site
does not retain its repository map, SOP and standards links, contributor-role
detail, or software-tooling inventory. The 2025-11-14 capture was restored as a
curated historical supplement.

The remaining archived files are an older duplicate GitHub capture, three
exact copies of the cohort-1 training webinar, and an older rendering of the
same NIH award. The cohort-1 webinar has genuinely historical dates and cohort
limits, but it is superseded by the active cohort-2 webinar and is intentionally
kept in the archive rather than treated as current D4D evidence.

### CM4AI

Two real omissions were found and restored:

- The March 2025 release records DOI `10.18130/V3/B35XWX`, a release-specific
  file inventory and checksums, and the 563-protein image composition.
- The June 2025 release records DOI `10.18130/V3/F3TD5R`, version 2.1, its file
  inventory and checksums, and the RGB immunofluorescence revision.

The current release page names these releases but does not preserve those
details. The other archived CM4AI inputs are a duplicate preprint extraction,
its DOI pointer, an older NIH RePORTER rendering, and a sparse older copy of the
current release page.

### VOICE

No distinct document was lost. The archived files resolve to:

- an older version of the current documentation site;
- exact duplicate DTUA copies, now represented by the complete Drive export;
- a Google Docs shell replaced by the complete IRB export;
- GitHub API metadata for the same documentation repository README;
- an older PhysioNet 1.1 capture; and
- an older NIH RePORTER rendering of the same award.

The historical Health Data Nexus 1.0 capture was reviewed separately. The
current PhysioNet 1.1 source preserves its dataset description, 12,523
recordings/306 participants, methods, de-identification, file organization,
release notes, license, DUA, and current DOI; current VOICE documentation also
retains the Health Data Nexus distribution context. The omitted differences
are stale platform metadata and the former "latest" DOI, so this is not a
missed current source.

## Remaining caveats

- The current NIH RePORTER text formatter captures the contact PI but not the
  complete co-investigator/program-officer roster visible in older rendered
  pages. This is an extraction-field limitation, not a missing-document case.
- CM4AI's input sheet still selects the October 2025 `K7TGEM` release while the
  project site advertises the newer `HIGT4C` release. The manifest records this
  upstream discrepancy and its verification URL.

After the three restorations and the AI_READI DOI metadata fix, no other known
D4D-relevant source category or substantive content represented in the prior
processed corpus is absent from the active corpus.

## Follow-up

The current-release gaps recorded above — AI_READI documentation at v2, CM4AI
`HIGT4C` present only as a verification URL, and VOICE stopping at PhysioNet
3.0.0 — were closed on 2026-07-24. See `input_refresh_2026-07-24.md`.
