# Organized Dataset Extraction Report

Generated: 2026-07-23 18:45:43

## Summary by Type

- **Web Page**: 8
- **PDF**: 5
- **NIH RePORTER Project**: 4
- **Dataverse Dataset**: 1
- **Google Drive**: 4
- **PhysioNet Dataset**: 2
- **GitHub Repository**: 1
- **FAIRhub Dataset**: 1

## Downloads by Column

### CM4AI
Directory: `CM4AI/`

#### Web Page (4)

- ✅ Row 2: `www_nature_com_articles-s41586-025-08878-3_row2.html`
  - Title: Multimodal cell maps as a foundation for structural and functional genomics | Nature
- ✅ Row 10: `cm4ai_org_row10.html`
  - Title: Cell Maps For AI (CM4AI) – Cell Maps For AI
- ✅ Row 11: `cm4ai_org_data-releases_row11.html`
  - Title: Data Releases – Cell Maps For AI (CM4AI)
- ✅ Row 15: `creativecommons_org_licenses-by-nc-sa_row15.html`
  - Title: 
      Deed - Attribution-NonCommercial-ShareAlike 4.0 International - Creative
      Commons
    

#### PDF (1)

- ✅ Row 4: `biorxiv_2024.05.21.589311v1_row4.pdf`

#### NIH RePORTER Project (1)

- ✅ Row 7: `reporter_nih_gov_project-details-11211616_row7.json`

#### Dataverse Dataset (1)

- ✅ Row 16: `dataverse_10.18130_V3_K7TGEM_row16.html`
  - Title: Cell Maps for Artificial Intelligence
  - DOI: doi:10.18130/V3/K7TGEM

### VOICE
Directory: `VOICE/`

#### Web Page (2)

- ✅ Row 2: `pmc_ncbi_nlm_nih_gov_articles-PMC12037532_row2.html`
  - Title: 
            The Bridge2AI-voice application: initial feasibility study of voice data acquisition through mobile health - PMC
        
- ✅ Row 10: `docs_b2ai-voice_org_row10.html`
  - Title: Bridge2AI - Voice

#### Google Drive (3)

- ✅ Row 5: `gdrive_1PiK_YlEoFhte1i4LMv7yAPCt2mRA-Si5_row5.pdf`
- ✅ Row 13: `gdrive_1gTFzAM-FoYlM_X9qF0s7fXoswmaz8IqN_row13.docx`
- ✅ Row 14: `gdrive_1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA_row14.pdf`

#### NIH RePORTER Project (1)

- ✅ Row 7: `reporter_nih_gov_project-details-11376382_row7.json`

#### PhysioNet Dataset (2)

- ✅ Row 17: `physionet_b2ai-voice_1.1_row17.html`
- ✅ Row 18: `physionet_b2ai-voice_3.0.0_row18.html`

#### GitHub Repository (1)

- ✅ Row 22: `github_eipm_bridge2ai-docs_row22.json`

### AI-READI
Directory: `AI_READI/`

#### PDF (3)

- ❌ Row 2: Failed - Expected a PDF payload, got text/html; charset=utf-8 (1817 bytes)
- ❌ Row 3: Failed - Expected a PDF payload, got text/html; charset="UTF-8" (244234 bytes)
- ✅ Row 11: `AI-READI-LICENSE-v1.0_row11.pdf`

#### NIH RePORTER Project (1)

- ✅ Row 7: `reporter_nih_gov_project-details-10471118_row7.json`

#### Web Page (1)

- ✅ Row 10: `docs_aireadi_org_docs-2_row10.html`
  - Title: About | Documentation for the AI-READI Dataset

#### FAIRhub Dataset (1)

- ✅ Row 12: `fairhub_dataset_2_row12.html`

#### Google Drive (1)

- ✅ Row 13: `gdrive_1rJsa5kySlBRRNhsO_WY7N3bfSKtqDi-Q_row13.docx`

### CHORUS
Directory: `CHORUS/`

#### NIH RePORTER Project (1)

- ✅ Row 7: `reporter_nih_gov_project-details-10472824_row7.json`

#### PDF (1)

- ✅ Row 9: `bridge2ai-for-clinical-care-informational-webinar-cohort-2_row9.pdf`

#### Web Page (1)

- ✅ Row 11: `chorus4ai_org_row11.html`
  - Title: CHoRUS – This repoitory is under review for potential modification in compliance with Administration directives.


## Duplicate URLs Skipped

- VOICE row 22: https://docs.b2ai-voice.org/
- AI-READI row 16: https://fairhub.io/datasets/2

## Errors

- Column: AI-READI, Row: 2
  - URL: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11800295/pdf/bmjopen-2024-097449.pdf
  - Error: Expected a PDF payload, got text/html; charset=utf-8 (1817 bytes)

- Column: AI-READI, Row: 3
  - URL: https://www.nature.com/articles/s42255-024-01165-x.pdf
  - Error: Expected a PDF payload, got text/html; charset="UTF-8" (244234 bytes)


## Canonical Promotion

- Selection manifest: `data/preprocessed/source_manifest.yaml`
- Freshly promoted sources: 24
- Retained validated fallbacks: 2
- Unresolved canonical sources: 0
  - `AI_READI/bmjopen-2024-097449_row2.pdf` retained: current refresh returned HTML instead of PDF
  - `AI_READI/s42255-024-01165-x_row3.pdf` retained: current refresh returned HTML instead of PDF

## Upstream Anomalies

- CM4AI: The page displays June 17, 2025 for its June 2026 release;
  Dataverse reports publication date 2026-06-17 and version 2 release time
  2026-07-15T20:28:19Z. The sheet still selects the October 2025 DOI
  `10.18130/V3/K7TGEM`.
