# Validated D4D Agent Processing Report

Generated: 2025-11-08 17:45:52

## Overall Summary

- **Files processed**: 11
- **Errors**: 4
- **Skipped**: 0

## Validation Summary

- **Downloads successful**: 14
- **Downloads failed**: 1
- **Content relevant to project**: 11
- **Content with limited relevance**: 3

## Results by Column

### AI_READI

**Validation Results:**
- Downloads: 5 successful, 1 failed
- Relevance: 4 relevant, 1 limited

#### Successfully Processed

- ✅ `docs_aireadi_org_docs-2_row8.txt` → `docs_aireadi_org_docs-2_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 8 (found: ai-readi, diabetes, fairhub)
- ✅ `fairhub_row13.json` → `fairhub_row13_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 4 (found: fairhub)
- ✅ `doi_row2.json` → `doi_row2_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 1 (found: aireadi)
- ✅ `doi_row9.json` → `doi_row9_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ⚠️ Limited relevance to AI_READI

#### Errors

- ❌ `docs_google_com_document-d_row11.txt` (stage: download_validation): Content appears to be incomplete or invalid
- ❌ `fairhub_row10.json` (stage: d4d_processing): Invalid YAML generated: while parsing a block mapping
  in "<unicode string>", line 1, column 1:
    id: "https://fairhub.io/datasets/2"
    ^
expected <block end>, but found '<scalar>'
  in "<unicode string>", line 3, column 111:
     ... AI_READI. Source type noted as "FAIRhub Dataset.""
                                         ^

### CHORUS

**Validation Results:**
- Downloads: 2 successful, 0 failed
- Relevance: 2 relevant, 0 limited

#### Successfully Processed

- ✅ `aim-ahead-bridge2ai-for-clinical-care-informational-webinar_row7.pdf` → `aim-ahead-bridge2ai-for-clinical-care-informational-webinar_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 4 (found: bridge2ai)
- ✅ `CHoRUS for Equitable AI.pdf` → `CHoRUS for Equitable AI_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 4 (found: chorus)

### CM4AI

**Validation Results:**
- Downloads: 4 successful, 0 failed
- Relevance: 2 relevant, 2 limited

#### Successfully Processed

- ✅ `doi_row3.json` → `doi_row3_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ⚠️ Limited relevance to CM4AI
- ✅ `dataverse_10.18130_V3_F3TD5R_row16.txt` → `dataverse_10.18130_V3_F3TD5R_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 6 (found: dataverse)
- ✅ `2024.05.21.589311v1.full.pdf` → `2024.05.21.589311v1.full_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ⚠️ Limited relevance to CM4AI

#### Errors

- ❌ `dataverse_10.18130_V3_B35XWX_row13.txt` (stage: d4d_processing): Invalid YAML generated: mapping values are not allowed here
  in "<unicode string>", line 147, column 147:
     ... e-Relevant Cell Lines. 2024. doi: http://doi.org/10.1101/2024.05 ... 
                                         ^

### VOICE

**Validation Results:**
- Downloads: 3 successful, 0 failed
- Relevance: 3 relevant, 0 limited

#### Successfully Processed

- ✅ `B2AI-Voice DTUA 2025 2025-09-04.pdf` → `B2AI-Voice DTUA 2025 2025-09-04_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 8 (found: voice, b2ai-voice)
- ✅ `healthnexus_row13.json` → `healthnexus_row13_d4d.yaml`
  - Download: ✅ Success
  - Relevance: ✅ Score 6 (found: voice, b2ai-voice, health data nexus)

#### Errors

- ❌ `physionet_b2ai-voice_1.1_row14.txt` (stage: d4d_processing): Invalid YAML generated: while parsing a block mapping
  in "<unicode string>", line 74, column 7:
          name: "Bridge2AI: Voice as a Bio ... 
          ^
expected <block end>, but found '<scalar>'
  in "<unicode string>", line 75, column 9:
            sourced, bioacoustic database to ... 
            ^

