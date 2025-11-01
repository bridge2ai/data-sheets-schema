# Validated D4D Agent Processing Report

Generated: 2025-09-08 23:05:42

## Overall Summary

- **Files processed**: 8
- **Errors**: 7
- **Skipped**: 2

## Validation Summary

- **Downloads successful**: 12
- **Downloads failed**: 5
- **Content relevant to project**: 10
- **Content with limited relevance**: 2

## Results by Column

### AI_READI

**Validation Results:**
- Downloads: 5 successful, 3 failed
- Relevance: 4 relevant, 1 limited

#### Successfully Processed

- ✅ `docs_aireadi_org_docs-2_row8.txt` → `docs_aireadi_org_docs-2_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 8 (found: ai-readi, diabetes, fairhub)
- ✅ `fairhub_row13.json` → `fairhub_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 4 (found: fairhub)
- ✅ `doi_row2.json` → `doi_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 1 (found: aireadi)

#### Errors

- ❌ `docs_google_com_document-d_row11.html` (stage: download_validation): Content appears to be incomplete or invalid
- ❌ `docs_aireadi_org_docs-2_row8.html` (stage: download_validation): Content appears to be incomplete or invalid
- ❌ `docs_google_com_document-d_row11.txt` (stage: download_validation): Content appears to be incomplete or invalid

#### Skipped

- ⏭️  `doi_row9.json`: Already exists
- ⏭️  `fairhub_row10.json`: Already exists

### CHORUS

**Validation Results:**
- Downloads: 1 successful, 0 failed
- Relevance: 1 relevant, 0 limited

#### Successfully Processed

- ✅ `aim-ahead-bridge2ai-for-clinical-care-informational-webinar_row7.pdf` → `aim-ahead-bridge2ai-for-clinical-care-informational-webinar_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 4 (found: bridge2ai)

### CM4AI

**Validation Results:**
- Downloads: 4 successful, 1 failed
- Relevance: 3 relevant, 1 limited

#### Successfully Processed

- ✅ `doi_row3.json` → `doi_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ⚠️ Limited relevance to CM4AI
- ✅ `dataverse_10.18130_V3_B35XWX_row13.html` → `dataverse_10.18130_V3_B35XWX_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 16 (found: cm4ai, microscopy, imaging, cellular, dataverse)

#### Errors

- ❌ `dataverse_10.18130_V3_F3TD5R_row16.txt` (stage: d4d_processing): Invalid YAML generated: mapping values are not allowed here
  in "<unicode string>", line 3, column 49:
     ... ive information I can extract is:
                                         ^
- ❌ `dataverse_10.18130_V3_F3TD5R_row16.html` (stage: d4d_processing): Invalid YAML generated: mapping values are not allowed here
  in "<unicode string>", line 3, column 75:
     ... le is a DOI in the URL parameter: doi:10.18130/V3/F3TD5R, but th ... 
                                         ^
- ❌ `dataverse_10.18130_V3_B35XWX_row13.txt` (stage: download_validation): Content contains error: not found

### VOICE

**Validation Results:**
- Downloads: 2 successful, 1 failed
- Relevance: 2 relevant, 0 limited

#### Successfully Processed

- ✅ `healthnexus_row13.json` → `healthnexus_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 6 (found: voice, b2ai-voice, health data nexus)
- ✅ `physionet_b2ai-voice_1.1_row14.txt` → `physionet_b2ai-voice_1.1_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 28 (found: voice, b2ai-voice, bridge2ai voice, vocal, speech, physionet, health data nexus)

#### Errors

- ❌ `physionet_b2ai-voice_1.1_row14.html` (stage: download_validation): Content appears to be incomplete or invalid

