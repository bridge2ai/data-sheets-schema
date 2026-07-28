# Upstream Source Discrepancies — GC Input Documents Sheet

**Verified:** 2026-07-24
**Applied upstream:** six cell corrections 2026-07-27, pediatric row insert
2026-07-28 — all six discrepancies actioned (see *Status* below)
**Sheet:** `1jBD6sTp6TDemy6v75PGAHSVz5yfIAXZ8zdDPbmOGATM`
([CSV export](https://docs.google.com/spreadsheets/d/1jBD6sTp6TDemy6v75PGAHSVz5yfIAXZ8zdDPbmOGATM/export?format=csv))
**Local counterpart:** `data/preprocessed/source_manifest.yaml`

The D4D corpus is built from the GC Input Documents sheet. Five of the sheet's
selections (in six cells) no longer point at the current upstream release, and
one current release is absent from the sheet entirely. The local manifest already captures
both the sheet-selected and the current release for each case, with a
`curation_note` stating which to prefer, so **D4D generation is not blocked**.
Correcting the sheet was the only way these stop recurring on the next refresh.
All of it is now applied (see *Status*) — five superseded selections corrected in
six cells, and the missing pediatric row inserted.

Every fact below was verified against the live upstream resource on 2026-07-24,
not merely copied from the manifest.

## Sheet coordinates

Columns in the CSV export: `A` = row label, `B` = CM4AI, `C` = VOICE,
`D` = AI-READI, `E` = CHORUS. Row numbers are CSV export rows; the row label is
given alongside each so the target cell is unambiguous if hidden rows shift the
numbering.

## Summary

| # | Project | Cell | Sheet selects | Current upstream | Nature |
|---|---------|------|---------------|------------------|--------|
| 1 | AI-READI | `D10` (documentation 1) | docs v2.0.0 | docs v3.0.0 | Superseded |
| 2 | AI-READI | `D12` + `D16` | FAIRhub `/datasets/2` | FAIRhub `/datasets/3` | Superseded |
| 3 | CM4AI | `B16` (data resource 1) | Dataverse `K7TGEM` | Dataverse `HIGT4C` | Superseded |
| 4 | VOICE | `C18` (data resource 3) | PhysioNet 3.0.0 | PhysioNet 3.1.0 | Superseded |
| 5 | VOICE | *(row inserted at 19)* | — | Pediatric v1.1.0 | Absent |
| 6 | CHORUS | col `E` | 3 sources only | — | Thin coverage |

## Status

Applied to the live sheet on **2026-07-27** via the `culturebot-data-downloader`
service account, using `spreadsheets.values.batchUpdate` (RAW). Each cell was
read before writing and refused on drift, then read back after. All six
verified.

| Cell | Was | Now | State |
|------|-----|-----|-------|
| `D10` | `docs.aireadi.org/docs/2/about` | `docs.aireadi.org/docs/3/about` | ✅ applied |
| `D12` | `fairhub.io/datasets/2` | `fairhub.io/datasets/3` | ✅ applied |
| `D16` | `fairhub.io/datasets/2` | `fairhub.io/datasets/3` | ✅ applied |
| `B16` | Dataverse `K7TGEM` | Dataverse `HIGT4C` | ✅ applied |
| `C18` | `physionet.org/…/b2ai-voice/3.0.0/` | `…/3.1.0/` | ✅ applied |
| `E16` | *(empty)* | Dataverse `XNBOPG` | ✅ applied — see §6, needs the crate-corpus guard |

**Item 5 (VOICE pediatric) applied 2026-07-28**, separately and after the six
cell edits, because it required inserting a row rather than overwriting a cell.
A new `data resource 4 (pediatric)` row was inserted at 19 with the VOICE column set to
`https://physionet.org/content/b2ai-voice-pediatric/1.1.0/`. See §5.

All six discrepancies are now actioned upstream.

Two backups, both restoring the live sheet exactly:

| File | State captured |
|------|----------------|
| `data/ATTIC/gsheet_backup_2026-07-28.json` | before any edit (22 rows) |
| `data/ATTIC/gsheet_backup_2026-07-28_post_cell_edits.json` | after the six cell edits, before the row insert (22 rows) |

Restoring the first undoes everything; restoring the second undoes only the row
insert. Note that neither is a formatting backup — values only.

Correcting the sheet does not by itself change the local corpus — the manifest
already carries both the superseded and current sources for each case. The
effect is on the *next* refresh, which will now select the current releases
without needing the `curation_note` overrides.

---

## 1. AI-READI — documentation points at dataset v2.0.0

**Cell `D10`** (row label `documentation 1`) selects
`https://docs.aireadi.org/docs/2/about`.

The docs site's version selector lists v1.0.0, v2.0.0, and v3.0.0, with
**v3.0.0 marked current**. The v3 page was last updated **2026-06-04**. The v2
documentation remains valid evidence about the v2.0.0 release but does not
describe the current dataset.

**Fix:** change `D10` to `https://docs.aireadi.org/docs/3/about`.

**Local handling:** both captured — `dataset_documentation` (v2, sheet-selected)
and `dataset_documentation_v3` (current, captured 2026-07-24). The v3 entry's
curation note instructs the generator to prefer it where the two disagree.

> **Trap for whoever fixes this:** `https://docs.aireadi.org/docs/4/about`
> returns HTTP 200 but serves the v3.0.0 content — the site silently falls back
> to the current version for out-of-range path segments. A 200 is not evidence
> that a version exists. Confirm against the version selector, which lists only
> v1–v3.

## 2. AI-READI — FAIRhub record points at the superseded v2.0.0

**Cells `D12`** (row label `documentation 3`) **and `D16`** (row label
`data resource 1`) both select `https://fairhub.io/datasets/2`.

That record is dataset **v2.0.0**, and the page states plainly:

> This version of the dataset is no longer accessible. Please refer to the
> latest version.

The current record is **`https://fairhub.io/datasets/3`** — v3.0.0, DOI
`10.60775/fairhub.3`, published 2025-11-17. `https://doi.org/10.60775/fairhub.3`
resolves to it.

The two records disagree materially on the dataset's headline figures, so citing
v2 propagates stale numbers:

| | v2.0.0 (`/datasets/2`) | v3.0.0 (`/datasets/3`) |
|---|---|---|
| Total size | 2.01 TB | 3.82 TB |
| File count | 165,051 | 356,343 |

This one was found while validating the input corpus, not from the version
sweep — the capture's own text carried the "no longer accessible" notice.

**Fix:** change both `D12` and `D16` to `https://fairhub.io/datasets/3`.

> **Related but out of scope:** `https://fairhub.io/datasets/4` is a distinct
> **"Mini Version"** of the dataset (100 participants, DOI
> `10.60775/fairhub.4`), published for pipeline development. It is a separate
> derivative dataset, not a version of the flagship one, and is deliberately not
> ingested.

**The page is a shell; the content is behind an API.** Static capture of either
record yields only ~1.3 KB of text, because fairhub.io is a JavaScript
application. An earlier revision of this note concluded from that the source
"corroborates facts; it does not describe the dataset" — wrong. Requesting
`https://fairhub.io/api/datasets/3` returns 133 KB of structured metadata,
including an **84-question healthsheet (81 answered)** spanning motivation,
composition, collection, preprocessing, labeling, uses, distribution, and
maintenance, plus `studyDescription`, `readme`, and `datasetDescription`.

That materially raises the stakes on this discrepancy: `/datasets/2` versus
`/datasets/3` is not two thin pages disagreeing about a byte count, it is two
different full metadata records.

**Local handling:** three entries — `fairhub_dataset` (v2, sheet-selected),
`fairhub_dataset_v3` (v3 HTML, retained for the human-facing URL and version
list), and `fairhub_dataset_v3_api` (the API record, captured 2026-07-27,
carrying the actual content).

## 3. CM4AI — data resource points at the October 2025 release

**Cell `B16`** (row label `data resource 1`) selects
`https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/K7TGEM`.

The current release is **`doi:10.18130/V3/HIGT4C`**. Verified from the Dataverse
API on 2026-07-24:

- `publicationDate`: 2026-06-17
- version: **2.0**, `versionState` RELEASED
- `releaseTime`: 2026-07-15T20:28:19Z
- 10 files (APMS, IF images, mass-spec, perturb-seq, release metadata)

```bash
curl -sSL "https://dataverse.lib.virginia.edu/api/datasets/:persistentId/?persistentId=doi:10.18130/V3/HIGT4C"
```

**Fix:** change `B16` to
`https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C`.

**Local handling:** `october_2025_dataverse_release` (K7TGEM, sheet-selected) and
`june_2026_dataverse_release` (HIGT4C, captured 2026-07-24) are both in the
manifest. The March 2025 (`B35XWX`) and June 2025 (`F3TD5R`) releases are
retained as historical supplements because the current release page names them
without preserving their DOIs, file inventories, or checksums.

### 3a. Separate upstream bugs — CM4AI release metadata

Not sheet issues; these belong to whoever maintains the CM4AI site and Dataverse
deposits. Item 1 was found in the 2026-07-24 sweep; items 2–5 were surfaced on
2026-07-27 by the D4D baseline generation run, which read all four release pages
side by side and recorded them as `anomalies` rather than silently picking a
value.

**1. Release page year is off by one.** `https://cm4ai.org/data-releases/` heads
the section **"June 2026 Data Release (Beta)"** but displays **"Released on:
June 17, 2025"**. Dataverse gives `publicationDate` **2026-06-17**. Anyone
reading the release page alone dates the current release a year early.
*Fix:* correct the displayed date to June 17, 2026.

**2. Version numbers are non-monotonic across the series.** Verified directly
against the Dataverse API on 2026-07-27:

| Release | Dataverse version | publicationDate |
|---|---|---|
| March 2025 `B35XWX` | 1.4 | 2025-03-03 |
| June 2025 `F3TD5R` | **3.1** | 2025-07-01 |
| October 2025 `K7TGEM` | 2.1 | 2025-10-31 |
| **June 2026 `HIGT4C` (current)** | **2.0** | 2026-06-17 |

The current release carries a **lower** version number than two of its
predecessors. Sorting CM4AI releases by version ranks the newest one third of
four. This is the most consequential of these defects, because version ordering
is exactly what a machine consumer would trust.
*Fix:* adopt a monotonic scheme across releases, or state explicitly that
version numbers are per-deposit and not comparable between releases.

**3. Description timestamps carried forward without updating.** The June 2026
release description ends with the parenthetical `(2025-06-30)` — the same
trailing date carried by the June 2025 and October 2025 descriptions. The text
was reused across releases without refreshing its timestamp.

**4. Creation and deposit dates frozen across all four releases.** Data Creation
Date and Deposit Date are both `2025-02-27` on March 2025, June 2025, October
2025 *and* June 2026, although files in later releases were published as late as
`2026-07-15`.

**5. Release name, publication date and file dates disagree.** The June 2025
release has `publicationDate` 2025-07-01 with image archives published
2025-10-22, so its name, its publication date and its file dates all indicate
different periods.

Taken together, items 2–5 mean **no date or version field on a CM4AI release can
currently be trusted to order the releases**. The only reliable ordering signal
we found is `releaseTime` on the latest version.

## 4. VOICE — data resource stops at PhysioNet 3.0.0

**Cell `C18`** (row label `data resource 3`) selects
`https://physionet.org/content/b2ai-voice/3.0.0/`.

The current adult release is **v3.1.0**, published **2026-05-01**, 833
participants. Confirmed that no v4.0.0 exists (404). Per the 3.1.0 release
notes, it is a minor update over 3.0.0 with **no new participants**: additional
data for some participants, repaired parquet files, new audio-quality and
per-audio metadata files, back-filled validated diagnosis information, and some
phenotype/gold-standard variable renaming.

**Fix:** change `C18` to `https://physionet.org/content/b2ai-voice/3.1.0/`.

**Local handling:** `physionet_3_0_0` (sheet-selected) and `physionet_3_1_0`
(current, captured 2026-07-24) are both in the manifest, with a preference note
on the latter. PhysioNet 1.1 is retained separately as the sheet's
`data resource 2`.

## 5. VOICE — pediatric dataset absent from the sheet

The sheet lists **no pediatric source in any row**, yet current VOICE
documentation advertises the pediatric release alongside the adult one
("B2AI-Voice v3.1.0 adult dataset and v1.1.0 pediatric dataset now available").

**Bridge2AI-Voice Pediatric Dataset v1.1.0** —
`https://physionet.org/content/b2ai-voice-pediatric/1.1.0/`

- Published 2026-05-01, credentialed access
- 300 participants aged 2–18; 23,533 derived recordings
- A **distinct PhysioNet project**, not a version of the adult `b2ai-voice`
  dataset — a separate cohort under a separate pediatric protocol, recruited at
  the Hospital for Sick Children (SickKids)
- PhysioNet hosts derived features only; **raw pediatric audio is distributed
  via Synapse** (`syn73617068`), not the adult DACO/PhysioNet route
- Pediatric v1.0.0 exists upstream but is superseded; v1.2.0 does not exist (404)

Because it is a distinct cohort rather than a newer version of an existing
source, no current cell is wrong — a row is missing.

**Fix:** add a `data resource 4 (pediatric)` row and set the VOICE column to
`https://physionet.org/content/b2ai-voice-pediatric/1.1.0/`. Row 19 held the
`metadata` label, so this needed an inserted row rather than an overwrite.

**Applied 2026-07-28.** A row was inserted at 19 via `insertDimension`
(`inheritFromBefore: false`), then `A19` = `data resource 4 (pediatric)` and
`C19` = the pediatric URL. Verified after the write: rows 1–18 untouched, the
four displaced rows (`metadata`, two blanks, and the trailing VOICE note)
shifted down byte-identically, and `metadata` now sits at row 20.

The label is parenthesised rather than left as a bare `data resource 4` on
purpose. Row 17 is `physionet.org/content/b2ai-voice/1.1/` and row 19 is
`physionet.org/content/b2ai-voice-pediatric/1.1.0/` — two rows apart, with
near-identical version numbers, on **different PhysioNet projects**. Nothing in
the version string distinguishes them, so the row label has to.

> **Row numbers below 19 are unchanged; anything at or past 19 has shifted down
> by one.** All cells cited elsewhere in this note (`B16`, `C18`, `D10`, `D12`,
> `D16`, `E16`) are above the insert and remain valid.

**Local handling:** ingested 2026-07-24 as `physionet_pediatric_1_1_0`. The
VOICE bundle now carries 11 sources.

## 6. CHORUS — thin sheet coverage

Distinct from the version discrepancies above, and lower confidence about intent
— flagging rather than asserting a defect.

Column `E` populates only three cells: NIH RePORTER project (`E7`), the AIM-AHEAD
cohort-2 webinar (`E9`), and `chorus4ai.org` (`E11`). There is **no publication,
no data resource, no license, no IRB, and no DUA row** for CHORUS, where the
other three projects populate most of those. The CHORUS bundle is consequently
the smallest by an order of magnitude (~36 KB vs 249–373 KB).

The local manifest already compensates with one historical supplement — the
CHoRUS GitHub organization overview, captured 2025-11-14 — retained because the
current project website does not preserve its repository, SOP, standards,
contributor-role, and software-tooling detail.

**A CHORUS data resource does exist.** While ingesting RO-Crate packages we found
that CHORUS publishes one on Dataverse:

`https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG`
— "Data Manifest for Collaborative Hospital Repository Uniting Standards (CHoRUS)
April 2026", crate version 1.0 Beta, published 2026-04-21. It carries the license
and access terms the sheet has no row for: a DUA at `chorus4ai.org/dataset/`,
`conditionsOfAccess` pointing to the September 2025 data agreement, IRB of record
(Mass General Brigham, protocol `#2022P000707`), and a `confidentialityLevel` of
HL7:2V.

So the answer to "does CHORUS have a public data resource to cite" is yes — the
sheet simply does not cite it.

**Suggested upstream action:** add `E16` (`data resource 1`) =
`https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG`,
and confirm whether a publication and license row can also be filled in.
**Applied 2026-07-27.**

### Consequence for the arm comparison — guarded 2026-07-28

Citing `XNBOPG` in the sheet means a sheet-driven refresh would download it into
`data/raw/CHORUS/`, putting the crate's own record on the *without-crate* side of
the comparison. CHORUS is where the crate contribution is largest and cleanest
(+22/+16/+20 fields, 12 stable across replicates), so this is the one GC where
that confound would cost the most.

**Scope of the leak, measured rather than assumed (2026-07-28).** The downloader's
`_process_dataverse` fetches only the landing page, not the crate files. That page
yields 14,044 characters of text and carries the DUA link
(`chorus4ai.org/dataset`) and the crate file *names*, but **not** the IRB protocol
`#2022P000707`, the institution, or the `confidentialityLevel` — those exist only
inside `ro-crate-metadata.json`. So the leak is partial, not wholesale. It is still
disqualifying, and the corpus-size effect is arguably the bigger problem: 14 KB
against a CHORUS document bundle of ~36 KB is a ~39% increase in the smallest
corpus, which shifts the baseline on its own.

**Guard.** `data/ro-crate_packages/crate_manifest.yaml` now declares
`document_corpus: exclude | allow | undecided` per project.
`rocrate_normalize.document_corpus_exclusions()` derives the skip-set from it —
from the crate manifest rather than a separate hand-kept list, so it cannot drift
from the crates actually held — and `organized_dataset_extractor.py` skips matching
URLs, recording them under `crate_corpus_skipped` rather than dropping them
silently. DOIs are matched in bare, `doi:`, `doi.org`, and `persistentId=` forms.

Two properties worth preserving if this is ever refactored:

- **It fails open.** `allow`, `undecided`, and a missing declaration all download
  normally. A wrong exclusion silently removes a real input document and shifts a
  baseline — much harder to notice than a wrong inclusion.
- **It is per-project, not blanket.** CM4AI's `HIGT4C` is the same shape of URL
  and is deliberately `allow`: it is the data release itself, already a curated
  document-corpus source (`june_2026_dataverse_release`), and the crate ships
  inside one of its 10 files rather than on the page. A blanket rule keyed on
  "is a crate DOI" would have dropped it and changed the CM4AI baseline.

AI-READI is `undecided` pending its crate link; the downloader prints a warning
each run so it cannot be forgotten.

---

## Coverage check

Every URL in the sheet is represented in `source_manifest.yaml` after
first-occurrence deduplication — there is no sheet source we fail to ingest.
(AI-READI's `https://fairhub.io/datasets/2` appears twice, at `D12`
`documentation 3` and `D16` `data resource 1`; it is ingested once as
`fairhub_dataset`.) The discrepancies above are the reverse case: current
upstream material the sheet does not yet select.

Corpus state after this pass: **35 sources** across the four projects (updated
2026-07-27 with the FAIRhub API record), every one with both a raw capture and a
processed text, zero preprocessing-quality failures, and 34 of 35 declared URLs
returning 2xx on re-check. The exception is
the AI-READI Zenodo license file URL, which returns 403 to automated fetches;
its DOI (`10.5281/zenodo.10642459`) resolves and the local capture is a genuine
9,165-character University of Washington Data License Agreement, so it is sound.

## Internal note — stale `_rowN` filename suffixes

Not an upstream issue, and no action needed; recorded so nobody mistakes these
for sheet coordinates.

Raw filenames carry a `_rowN` suffix from the sheet row they were captured from
at capture time. Some no longer match current sheet rows:

- `dataverse_10.18130_V3_B35XWX_row16.html` and
  `dataverse_10.18130_V3_K7TGEM_row16.html` both claim `row16` — B35XWX was
  captured 2026-04-24 when the sheet's `data resource 1` held that release.
- `dataverse_10.18130_V3_F3TD5R_row19.html` claims `row19`, which is now the
  empty `metadata` label row.

Sources captured after the convention was relaxed use a date suffix instead
(`_2026-07-24`), which does not go stale. The manifest `id` and `url` fields are
authoritative for identity; the filename suffix is not.
