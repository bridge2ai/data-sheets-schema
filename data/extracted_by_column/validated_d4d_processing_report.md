# Validated D4D Agent Processing Report

Generated: 2025-09-16 18:03:53

## Overall Summary

- **Files processed**: 6
- **Errors**: 4
- **Skipped**: 0

## Validation Summary

- **Downloads successful**: 8
- **Downloads failed**: 2
- **Content relevant to project**: 7
- **Content with limited relevance**: 1

## Results by Column

### AI_READI

**Validation Results:**
- Downloads: 3 successful, 1 failed
- Relevance: 3 relevant, 0 limited

#### Successfully Processed

- ✅ `docs_aireadi_org_docs-2_row8.txt` → `docs_aireadi_org_docs-2_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 8 (found: ai-readi, diabetes, fairhub)
- ✅ `doi_row2.json` → `doi_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 1 (found: aireadi)

#### Errors

- ❌ `fairhub_row13.json` (stage: d4d_processing): Invalid YAML generated: mapping values are not allowed here
  in "<unicode string>", line 3, column 71:
     ... h identifier 2. Project category: AI_READI.
                                         ^
- ❌ `docs_google_com_document-d_row11.txt` (stage: download_validation): Content appears to be incomplete or invalid

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
- Downloads: 2 successful, 1 failed
- Relevance: 1 relevant, 1 limited

#### Successfully Processed

- ✅ `doi_row3.json` → `doi_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ⚠️ Limited relevance to CM4AI
- ✅ `dataverse_10.18130_V3_F3TD5R_row16.txt` → `dataverse_10.18130_V3_F3TD5R_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 6 (found: dataverse)

#### Errors

- ❌ `dataverse_10.18130_V3_B35XWX_row13.txt` (stage: download_validation): Content contains error: not found

### VOICE

**Validation Results:**
- Downloads: 2 successful, 0 failed
- Relevance: 2 relevant, 0 limited

#### Successfully Processed

- ✅ `healthnexus_row13.json` → `healthnexus_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 6 (found: voice, b2ai-voice, health data nexus)

#### Errors

- ❌ `physionet_b2ai-voice_1.1_row14.txt` (stage: d4d_processing): Invalid YAML generated: mapping values are not allowed here
  in "<unicode string>", line 3, column 23:
    title: Bridge2AI-Voice: An ethically-sourced, diverse  ... 
                          ^

