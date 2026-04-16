# D4D GitHub Assistant Determinism - Verification Guide

**Date**: 2025-02-10
**Status**: Ready for Phase 3 Testing
**Prerequisite**: Implementation Phases 1-2 Complete ✅

## Quick Verification Checklist

Use this guide to verify the GitHub D4D Assistant determinism implementation.

## 1. Verify Files Created

```bash
# Check all new files exist
ls -lh .github/workflows/d4d_assistant_deterministic.config
ls -lh src/github/generate_d4d_metadata.py
ls -lh src/github/validate_d4d_completeness.py
ls -lh src/github/validate_prerequisites.sh
ls -lh data/sheets_d4dassistant/README.md

# Check scripts are executable
test -x src/github/generate_d4d_metadata.py && echo "✓ Metadata generator executable"
test -x src/github/validate_d4d_completeness.py && echo "✓ Completeness validator executable"
test -x src/github/validate_prerequisites.sh && echo "✓ Prerequisites validator executable"
```

**Expected**: All files exist and scripts are executable.

## 2. Test Prerequisites Validation

### 2.1 Test File Mode (Should Fail - No Input Files)

```bash
./src/github/validate_prerequisites.sh --dataset test --mode file

# Expected output:
# ✓ Schema file found
# ✓ System prompt found
# ✓ User prompt found
# ✓ Config file found
# ✗ Input files not found (expected - we haven't created test inputs)
# ❌ Prerequisites validation failed
```

**Expected exit code**: `1` (failure)

### 2.2 Create Test Input Files

```bash
# Create test input directory and files
mkdir -p data/sheets_d4dassistant/inputs/test
echo "Test documentation for dataset" > data/sheets_d4dassistant/inputs/test/doc1.txt
echo "Additional metadata" > data/sheets_d4dassistant/inputs/test/doc2.txt

# Re-run validation
./src/github/validate_prerequisites.sh --dataset test --mode file
```

**Expected**: Input files check now passes (✓), but may still fail on missing Python dependencies or API key.

### 2.3 Test URL Mode

```bash
./src/github/validate_prerequisites.sh \
  --dataset test \
  --mode url \
  --urls "https://example.com https://github.com"

# Expected:
# URLs accessibility checked (may show warnings for non-200 status)
```

## 3. Test Completeness Validation

### 3.1 Test with Comprehensive D4D (Should Pass)

```bash
# Use an existing comprehensive D4D file
python3 src/github/validate_d4d_completeness.py \
  data/d4d_concatenated/curated/AI_READI_curated.yaml

# Expected output:
# ✅ D4D Completeness Report
# Quality Level: COMPREHENSIVE or ACCEPTABLE
# ✅ QUALITY CHECK PASSED

echo $?  # Should be 0
```

### 3.2 Create Minimal Test D4D (Should Pass with Warning)

```bash
# Create minimal test file
cat > test_minimal_d4d.yaml << 'EOF'
id: test_dataset
name: Test Dataset
motivation:
  purposes:
    - id: test:purpose:1
      description: Test purpose
composition:
  instances:
    - id: test:instance:1
      description: Test instance
collection_process:
  how_was_data_acquired: Test acquisition
uses:
  tasks:
    - id: test:task:1
      description: Test task
EOF

# Validate
python3 src/github/validate_d4d_completeness.py test_minimal_d4d.yaml

# Expected:
# Quality Level: MINIMAL or ACCEPTABLE
# ✅ QUALITY CHECK PASSED (but warning about minimal quality)

echo $?  # Should be 0
```

### 3.3 Create Insufficient Test D4D (Should Fail)

```bash
# Create insufficient test file
cat > test_insufficient_d4d.yaml << 'EOF'
id: test_dataset
name: Test Dataset
EOF

# Validate
python3 src/github/validate_d4d_completeness.py test_insufficient_d4d.yaml

# Expected:
# Quality Level: INSUFFICIENT
# 🚫 PR CREATION BLOCKED

echo $?  # Should be 1 (failure)
```

### 3.4 Test Missing ID (Should Fail)

```bash
# Create file missing required field
cat > test_no_id.yaml << 'EOF'
name: Test Dataset
description: Test description
EOF

# Validate
python3 src/github/validate_d4d_completeness.py test_no_id.yaml

# Expected:
# ❌ Required Fields Missing: id
# 🚫 PR CREATION BLOCKED

echo $?  # Should be 1
```

## 4. Test Metadata Generation

### 4.1 Install Dependencies (If Not Already Installed)

```bash
pip install pyyaml anthropic
```

### 4.2 Generate Metadata (File Mode)

```bash
# Create test D4D file
cat > data/sheets_d4dassistant/test_d4d.yaml << 'EOF'
id: test_dataset
name: Test Dataset
description: Test description
EOF

# Generate metadata
python3 src/github/generate_d4d_metadata.py \
  --d4d-file data/sheets_d4dassistant/test_d4d.yaml \
  --dataset-name test \
  --input-dir data/sheets_d4dassistant/inputs/test \
  --issue-number 42

# Expected output:
# 📋 Generating D4D extraction metadata...
# ✅ Metadata saved: data/sheets_d4dassistant/test_d4d_metadata.yaml
# 📊 Metadata Summary: (hashes, timestamps, etc.)
```

### 4.3 Verify Metadata Structure

```bash
# Check metadata file exists
ls -lh data/sheets_d4dassistant/test_d4d_metadata.yaml

# View metadata
cat data/sheets_d4dassistant/test_d4d_metadata.yaml

# Verify key fields present
grep -E "(extraction_metadata|input_documents|datasheets_schema|llm_model|prompts|provenance)" \
  data/sheets_d4dassistant/test_d4d_metadata.yaml

# Check SHA-256 hashes present
grep sha256_hash data/sheets_d4dassistant/test_d4d_metadata.yaml
```

**Expected**: Metadata file with all sections and SHA-256 hashes.

### 4.4 Generate Metadata (URL Mode)

```bash
# Generate metadata with URLs
python3 src/github/generate_d4d_metadata.py \
  --d4d-file data/sheets_d4dassistant/test_d4d.yaml \
  --dataset-name test \
  --input-sources "https://example.com/doc1" "https://example.com/doc2"

# Check input_documents section has URLs and hashes
grep -A5 "input_documents:" data/sheets_d4dassistant/test_d4d_metadata.yaml
```

**Expected**: Metadata with URL hashes in input_documents section.

## 5. Verify Configuration File

```bash
# Check config file structure
cat .github/workflows/d4d_assistant_deterministic.config

# Verify key settings
grep -A3 "^model:" .github/workflows/d4d_assistant_deterministic.config
grep "temperature:" .github/workflows/d4d_assistant_deterministic.config
grep "block_threshold:" .github/workflows/d4d_assistant_deterministic.config
```

**Expected**:
```yaml
model:
  name: claude-sonnet-4-5-20250929
  temperature: 0.0

validation:
  block_threshold: minimal
```

## 6. Verify Workflow File Updates

```bash
# Check workflow has deterministic parameters
grep -A3 "# Deterministic settings" .github/workflows/d4d-agent.yml
grep "model:" .github/workflows/d4d-agent.yml
grep "temperature:" .github/workflows/d4d-agent.yml
```

**Expected**:
```yaml
# Deterministic settings for reproducible D4D generation
model: 'claude-sonnet-4-5-20250929'
temperature: '0.0'
max-tokens: '16000'
```

## 7. Verify Instruction File Updates

### 7.1 Check Create Instructions

```bash
# Check for new sections
grep "## Deterministic Generation Settings" .github/workflows/d4d_assistant_create.md
grep "### 0. Validate Prerequisites" .github/workflows/d4d_assistant_create.md
grep "### 6. Generate Comprehensive Metadata" .github/workflows/d4d_assistant_create.md
grep "### 7b. Completeness Validation" .github/workflows/d4d_assistant_create.md
```

**Expected**: All new sections present.

### 7.2 Check Edit Instructions

```bash
# Check for new sections
grep "## Deterministic Generation Settings" .github/workflows/d4d_assistant_edit.md
grep "### 5. Regenerate Metadata" .github/workflows/d4d_assistant_edit.md
grep "### 6b. Completeness Validation" .github/workflows/d4d_assistant_edit.md
```

**Expected**: All new sections present.

## 8. Verify Directory Structure

```bash
# Check directory structure
ls -lh data/sheets_d4dassistant/
ls -lh data/sheets_d4dassistant/inputs/
ls -lh data/sheets_d4dassistant/fetched/

# Check README exists
cat data/sheets_d4dassistant/README.md | head -20
```

**Expected**: Directories created with README documentation.

## 9. Integration Test Preparation

### 9.1 Prerequisites for Live Test

Before testing with actual GitHub Assistant:

```bash
# 1. Check ANTHROPIC_API_KEY is set (for assistant)
echo $ANTHROPIC_API_KEY | cut -c1-20

# 2. Verify GitHub token permissions
gh auth status

# 3. Create test issue (optional)
gh issue create --title "Test D4D Assistant Determinism" \
  --body "Testing deterministic D4D generation with @d4dassistant"
```

### 9.2 End-to-End Test Plan

1. Create GitHub issue with D4D request
2. Provide test documentation (files or URLs)
3. Mention `@d4dassistant`
4. Observe workflow execution
5. Verify prerequisites checked first
6. Verify D4D generated
7. Verify metadata created
8. Verify completeness validated
9. Verify PR created (if pass) or blocked (if fail)
10. Check PR contains all three files (YAML, metadata, HTML)

## 10. Cleanup Test Files

```bash
# Remove test files created during verification
rm -f test_minimal_d4d.yaml
rm -f test_insufficient_d4d.yaml
rm -f test_no_id.yaml
rm -rf data/sheets_d4dassistant/inputs/test/
rm -f data/sheets_d4dassistant/test_d4d.yaml
rm -f data/sheets_d4dassistant/test_d4d_metadata.yaml
```

## Verification Status

After running all tests, check:

- [ ] All files created and executable
- [ ] Prerequisites validation works (fail fast)
- [ ] Completeness validation works (quality levels, exit codes)
- [ ] Metadata generation works (file and URL modes)
- [ ] Configuration file has correct settings
- [ ] Workflow file has deterministic parameters
- [ ] Instruction files have new sections
- [ ] Directory structure exists with README

## Troubleshooting

### Prerequisites Validation Fails

**Issue**: Missing Python dependencies
**Fix**: `pip install pyyaml anthropic`

**Issue**: ANTHROPIC_API_KEY not set
**Fix**: `export ANTHROPIC_API_KEY=sk-ant-...`

### Completeness Validation Unexpected Results

**Issue**: Comprehensive file shows as insufficient
**Fix**: Check if file uses flat vs modular schema structure. Validator is designed for modular D4D_* sections.

### Metadata Generation Fails

**Issue**: Import error for yaml or anthropic
**Fix**: Install dependencies with pip

**Issue**: File not found errors
**Fix**: Check paths are correct and files exist

## Next Steps After Verification

1. **Phase 3 Integration Testing**: Test with actual GitHub Assistant
2. **Phase 4 Verification**: Compare with batch extraction outputs
3. **Fine-tuning**: Adjust thresholds if needed based on real usage
4. **Documentation**: Update with any lessons learned

## Support

For issues or questions:
- Check `notes/IMPLEMENTATION_SUMMARY.md` for complete details
- Review instruction files in `.github/workflows/`
- Check `data/sheets_d4dassistant/README.md` for usage guidance
