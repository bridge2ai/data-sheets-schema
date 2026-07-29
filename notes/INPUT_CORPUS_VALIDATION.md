# Input Corpus Validation — 2026-07-24 (updated 2026-07-27)

Gate run before D4D regeneration, confirming every source in
`data/preprocessed/source_manifest.yaml` is present, faithfully extracted, and
still live.

**Verdict: the corpus is sound and cleared for generation.** 35 sources, zero
capture failures. One real defect was found and fixed (a superseded FAIRhub
record), and two sources are flagged as low-value rather than broken.

## What was checked

1. **Presence** — every manifest entry has both a raw capture and a processed
   `.txt`, with no orphans in either direction.
2. **Extraction health** — `make validate-preprocessing` (empty / stub /
   low-extraction / missing / unexpected).
3. **Failure signatures** — regex sweep of processed text for login walls,
   JavaScript shells, bot-blocks, 404 bodies, and paywalls, with every hit read
   in context rather than trusted as a verdict.
4. **Extraction ratio** — processed characters ÷ raw bytes, to surface captures
   that technically pass but yield near-nothing.
5. **Liveness** — HTTP re-check of all 35 declared URLs.

## Results

| Check | Result |
|-------|--------|
| Sources | 35 (AI_READI 10, CHORUS 4, CM4AI 10, VOICE 11) |
| Raw + processed present | 35 / 35 |
| `make validate-preprocessing` | 35 checked, 0 problematic, 0 missing, 0 unexpected |
| Failure-signature hits | 6, **all verified false positives** |
| URLs returning 2xx | 34 / 35 (the exception is sound — see below) |

### The 6 signature hits were all real page vocabulary

Worth recording so a future run does not re-litigate them:

- **Four Dataverse captures** (`march_2025`, `june_2025`, `october_2025`,
  `june_2026`) matched *"request access"* — this is Dataverse's own **"Restrict
  Access"** help-modal boilerplate ("People who want to use the restricted files
  can request access by default…"), embedded in every dataset page. The
  `march_2025` capture additionally matched *"page not found"* from the same help
  text, describing what happens to an expired Preview URL.
- **`VOICE/project_documentation`** matched *"request access"* in the sentence
  "can request access by emailing" — genuine content about controlled audio
  access.
- **`CHORUS/github_organization_overview`** matched it in the contact block
  ("Request access: …@emory.edu").

Side note: the Dataverse captures each carry ~2–3 KB of Dataverse UI help text.
Not a defect, but it is boilerplate the generator will see.

### The one non-2xx URL is fine

`AI_READI/dataset_license` —
`https://zenodo.org/records/10642459/files/AI-READI-LICENSE-v1.0.pdf?download=1`
returns **403** to automated fetches (Zenodo blocks scripted downloads of file
URLs). Its DOI `10.5281/zenodo.10642459` resolves 200, and the local capture is a
genuine 9,165-character University of Washington Data License Agreement. No
action needed; do not "fix" this by re-downloading.

## Defect found and fixed: superseded FAIRhub record

`AI_READI/fairhub_dataset` (`https://fairhub.io/datasets/2`) passed every
mechanical check but its own text reads:

> This version of the dataset is no longer accessible. Please refer to the
> latest version.

It is the **v2.0.0** record, carrying stale headline figures (2.01 TB / 165,051
files) against the current v3.0.0 (3.82 TB / 356,343 files).

**Action taken:** captured `https://fairhub.io/datasets/3` as
`fairhub_dataset_v3` (DOI `10.60775/fairhub.3`, published 2025-11-17), with a
curation note preferring it; kept the v2 record as evidence about the v2.0.0
release. Written up as discrepancy §2 in
`notes/UPSTREAM_SOURCE_DISCREPANCIES.md`.

This is exactly the class of problem the ratio check exists to surface: the v2
record scored the **lowest HTML extraction ratio in the corpus** (0.46%), which
is what prompted reading it closely.

## Low-value but not broken

Flagged so nobody expects more from them than they contain:

- **`fairhub_dataset` / `fairhub_dataset_v3`** — static HTML capture of a 293 KB
  FAIRhub page yields ~1.3 KB of text (identity, size, license, keywords,
  version list). Retained to corroborate the human-facing URL and version list.

  > **Superseded 2026-07-27 — and this entry was wrong about the cause.** It read
  > "FAIRhub is a JavaScript application… useful for corroborating facts, not for
  > description," which blamed the platform. FAIRhub is not thin; the *capture
  > method* was. The content is served by an API at
  > `https://fairhub.io/api/datasets/3`, now ingested as
  > `fairhub_dataset_v3_api` — 167 KB of text including an **84-question
  > healthsheet, 81 answered**. Lesson worth keeping: for a JS application, a low
  > extraction ratio is a signal to look for an API, not to write the source off.
- **`CHORUS/project_documentation`** (2,614 chars from 101 KB) and
  **`CM4AI/project_documentation`** (3,287 from 278 KB) — navigation-heavy
  marketing homepages. The content is real but thin.

Also noted, not a capture problem: the CHORUS site currently carries a banner
reading *"This repoitory is under review for potential modification in compliance
with Administration directives"* (typo upstream). The same notice appears on the
FAIRhub AI-READI record. It will appear in the evidence bundle.

## Extraction ratios

PDF and DOCX ratios are low by nature (binary containers) and are not meaningful
signals. Among HTML sources the range is 0.46%–32%; everything below 1.5% was
read directly. The four NIH RePORTER sources sit at ~99% because they were
captured as text.

## Corpus inventory

| Project | Source id | Type | Raw | Chars | Note |
|---------|-----------|------|-----|-------|------|
| AI_READI | `bmj_protocol_publication` | publication | pdf | 49,564 | |
| AI_READI | `nature_metabolism_publication` | publication | pdf | 17,690 | |
| AI_READI | `nih_reporter_project` | NIH project page | txt | 4,471 | |
| AI_READI | `dataset_documentation` | documentation | html | 4,434 | superseded by v3 |
| AI_READI | `dataset_documentation_v3` | documentation | html | 4,334 | added 2026-07-24 |
| AI_READI | `dataset_license` | license | pdf | 9,165 | |
| AI_READI | `fairhub_dataset` | data resource | html | 1,362 | superseded by v3 |
| AI_READI | `fairhub_dataset_v3` | data resource | html | 1,294 | added 2026-07-24 |
| AI_READI | `fairhub_dataset_v3_api` | structured metadata | json | 167,136 | added 2026-07-27; 84-question healthsheet |
| AI_READI | `irb_protocol` | IRB | docx | 150,378 | |
| CHORUS | `nih_reporter_project` | NIH project page | txt | 5,172 | |
| CHORUS | `cohort_2_webinar` | tutorial | pdf | 15,755 | |
| CHORUS | `project_documentation` | documentation | html | 2,614 | thin |
| CHORUS | `github_organization_overview` | historical documentation | pdf | 8,950 | historical supplement |
| CM4AI | `nature_publication` | publication | html | 130,328 | |
| CM4AI | `biorxiv_preprint` | preprint | pdf | 53,341 | |
| CM4AI | `nih_reporter_project` | NIH project page | txt | 2,941 | |
| CM4AI | `project_documentation` | documentation | html | 3,287 | thin |
| CM4AI | `data_release_documentation` | documentation | html | 3,873 | date bug upstream |
| CM4AI | `dataset_license` | license | html | 5,184 | |
| CM4AI | `march_2025_dataverse_release` | historical data release | html | 27,505 | historical supplement |
| CM4AI | `june_2025_dataverse_release` | historical data release | html | 29,240 | historical supplement |
| CM4AI | `october_2025_dataverse_release` | data resource | html | 29,080 | superseded by HIGT4C |
| CM4AI | `june_2026_dataverse_release` | data resource | html | 27,433 | added 2026-07-24 |
| VOICE | `feasibility_publication` | publication | html | 46,874 | |
| VOICE | `audiomics_white_paper` | white paper | pdf | 13,290 | |
| VOICE | `nih_reporter_project` | NIH project page | txt | 6,165 | |
| VOICE | `project_documentation` | documentation | html | 69,042 | |
| VOICE | `irb_protocol` | IRB | docx | 76,708 | |
| VOICE | `data_transfer_use_agreement` | DUA | pdf | 16,417 | |
| VOICE | `physionet_1_1` | data resource | html | 22,922 | |
| VOICE | `physionet_3_0_0` | data resource | html | 40,475 | superseded by 3.1.0 |
| VOICE | `physionet_3_1_0` | data resource | html | 41,682 | added 2026-07-24 |
| VOICE | `physionet_pediatric_1_1_0` | data resource | html | 30,426 | added 2026-07-24 |
| VOICE | `documentation_repository` | documentation | md | 1,303 | |

Bundle sizes after re-concatenation: AI_READI 421 KB, CHORUS 36 KB, CM4AI 323 KB,
VOICE 378 KB. (AI_READI grew from 252 KB when the FAIRhub API record was added
on 2026-07-27; ~48 KB of that is a file/directory inventory carrying little
descriptive content.)

## Note on curation notes in the evidence stream

`preprocess_sources.py` prepends a `SOURCE METADATA` header to each processed
file that includes the manifest's `curation_note`. This is by design — it is how
"prefer v3 over v2" reaches the generating agent — but it means editorial prose
is part of the evidence bundle. Verified as intended behaviour, not
contamination; recording it because it looks surprising on first encounter.
