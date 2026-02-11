# Test Issue: Create D4D Datasheet for CM4AI Dataset

**Issue Type**: D4D Creation Test
**Dataset**: CM4AI (Common Mind for Artificial Intelligence)
**Test Date**: 2025-02-10

## Request

@d4dassistant Please create a comprehensive D4D datasheet for the CM4AI dataset using the input documents provided in this repository.

## Dataset Information

**Dataset Name**: CM4AI (Common Mind for Artificial Intelligence)
**Project**: Bridge2AI Common Mind Consortium
**Purpose**: Multi-modal dataset for AI research in mental health

## Input Documents Location

The preprocessed input documents are located in:
```
data/sheets_d4dassistant/inputs/CM4AI/
```

**Available files** (6 total, ~2,978 lines):
1. `2024.05.21.589311v1.full.txt` (53K) - Research paper
2. `RePORT ⟩ RePORTER - CM4AI.txt` (5.7K) - NIH grant report
3. `creativecommons_org_licenses-by-nc-sa_row15.txt` (5.6K) - License information
4. `dataverse_10.18130_V3_B35XWX_row16.txt` (27K) - Dataset documentation
5. `dataverse_10.18130_V3_F3TD5R_row19.txt` (29K) - Additional dataset info
6. `doi_row3.json` (123B) - Metadata

## Expected Workflow

When the D4D Assistant processes this request, it should:

1. ✅ **Validate Prerequisites**
   - Schema file exists
   - Prompt files exist
   - Input files accessible (6 files in `data/sheets_d4dassistant/inputs/CM4AI/`)
   - Output directory ready

2. 📖 **Study Schema**
   - Load D4D schema from `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
   - Review reference examples
   - Understand field structure

3. 📥 **Process Input Documents**
   - Read all 6 files
   - Extract D4D-relevant metadata
   - Map information to schema classes

4. 📝 **Generate D4D YAML**
   - Create `data/sheets_d4dassistant/CM4AI_d4d.yaml`
   - Populate with deterministic generation (temperature=0.0)
   - Use schema field names exactly

5. 🔐 **Generate Metadata**
   - Create `data/sheets_d4dassistant/CM4AI_d4d_metadata.yaml`
   - Include SHA-256 hashes for all inputs
   - Track git commit, model settings, prompts
   - Record processing environment

6. ✅ **Validate Quality**
   - **Schema validation**: Must pass LinkML validation
   - **Completeness check**: Must meet minimal threshold (4+ sections, 50+ slots, 100+ lines)
   - If validation fails → DO NOT create PR

7. 🌐 **Generate HTML Preview**
   - Create `data/sheets_d4dassistant/CM4AI_d4d.html`
   - Human-readable format for review

8. 📤 **Create Pull Request**
   - Branch: `d4d/add-cm4ai-datasheet`
   - Include all three files (YAML, metadata, HTML)
   - Provide summary of extracted metadata
   - Link back to this issue

## Test Objectives

This test issue validates:

- ✅ **Deterministic generation**: temperature=0.0, date-pinned model
- ✅ **File-based input mode**: Reading from `data/sheets_d4dassistant/inputs/`
- ✅ **Prerequisites validation**: Fail-fast checks before generation
- ✅ **Metadata generation**: Comprehensive provenance tracking
- ✅ **Completeness validation**: Quality gates before PR
- ✅ **GitHub integration**: Issue → PR workflow
- ✅ **Documentation**: Clear communication with user

## Expected Output Files

After processing, the following files should be created:

### 1. D4D YAML Datasheet
**Location**: `data/sheets_d4dassistant/CM4AI_d4d.yaml`
**Expected content**:
- `id`: Dataset identifier
- `name`: CM4AI or Common Mind for Artificial Intelligence
- `motivation`: Purpose, tasks, addressing_gaps
- `composition`: Instances, subsets, instance_count
- `collection_process`: Acquisition methodology
- `preprocessing`: Preprocessing steps and software
- `uses`: Recommended and not-recommended uses
- `distribution`: Format, access, requirements
- `maintenance`: Plan, version, contact
- `human_subjects`: IRB, consent, protections
- `ethics_and_data_protection`: Reviews, security
- `data_governance`: Stewards, license, terms

### 2. Metadata File
**Location**: `data/sheets_d4dassistant/CM4AI_d4d_metadata.yaml`
**Expected sections**:
```yaml
extraction_metadata:
  timestamp, extraction_id, extraction_type, input_mode: file
input_documents:
  - 6 files with SHA-256 hashes
datasheets_schema:
  sha256_hash: <schema hash>
llm_model:
  model_name: claude-sonnet-4-5-20250929
  temperature: 0.0
prompts:
  system_prompt_hash: <hash>
  user_prompt_hash: <hash>
provenance:
  git_commit: <current commit>
```

### 3. HTML Preview
**Location**: `data/sheets_d4dassistant/CM4AI_d4d.html`
**Purpose**: Human-readable view for reviewers

## Success Criteria

✅ **Prerequisites pass**: All files found, validation succeeds
✅ **Schema validation passes**: YAML conforms to D4D schema
✅ **Completeness check passes**: Meets minimal quality threshold
✅ **Metadata generated**: Complete provenance tracking
✅ **PR created**: With all three files
✅ **Clear communication**: Comments in issue and PR

## Troubleshooting

If the assistant encounters issues:

### Missing Input Files
- Check: `ls data/sheets_d4dassistant/inputs/CM4AI/`
- Should see 6 files

### Schema Validation Fails
- Review error messages
- Check field names against schema
- Fix and regenerate

### Completeness Check Fails
- Review metrics (sections, slots, lines)
- May need more detailed extraction
- Consider adding more content

### API Issues
- Check `ANTHROPIC_API_KEY` is set
- Verify API access

## Notes

- This is a **test issue** to validate the deterministic D4D assistant implementation
- All components (Phases 1-3) have been implemented and tested
- This represents the first end-to-end workflow test
- Results will inform Phase 4 (Verification and Comparison)

## Related Documentation

- Implementation: `IMPLEMENTATION_SUMMARY.md`
- Testing: `PHASE3_TESTING_RESULTS.md`
- Verification: `VERIFICATION_GUIDE.md`
- Instructions: `.github/workflows/d4d_assistant_create.md`
- Config: `.github/workflows/d4d_assistant_deterministic_config.yaml`

---

**Test Context**: Phase 3 → Phase 4 transition
**Repository Branch**: `2025_issue_fixes`
