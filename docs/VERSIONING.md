# D4D Datasheet Versioning Guide

This document explains the versioning process for Bridge2AI D4D (Datasheets for Datasets) HTML publications.

## Version Numbering

D4D datasheets use **sequential integer versioning** (v1, v2, v3, etc.). Each version represents a stable snapshot of the datasheets published to GitHub Pages.

### Current Version

**v5** - Published December 2024
- Method: `claudecode_agent` (Claude Code with Task tool for parallel extraction)
- Projects: AI_READI, CHORUS, CM4AI, VOICE
- Location: https://bridge2ai.github.io/data-sheets-schema/html_output/

## When to Increment Versions

Create a new version when:

1. **Schema Changes**: The D4D LinkML schema has been modified in ways that affect datasheet structure or content
2. **Source Updates**: New or updated source documents are available for the Bridge2AI projects
3. **Method Improvements**: The extraction/synthesis method has been significantly improved
4. **Error Corrections**: Substantial errors or omissions in the current version need correction
5. **Quarterly Updates**: Regular updates to keep datasheets current (recommended every 3-6 months)

**Do NOT create new versions for**:
- Minor typo fixes
- CSS/styling changes only
- Documentation updates
- Schema changes that don't affect generated content

## Versioning Workflow

### Prerequisites

Ensure you have:
- Updated D4D YAML files in `data/d4d_concatenated/claudecode_agent/`
- Generated HTML files in `data/d4d_html/concatenated/claudecode_agent/`
- Validated all YAML files against the schema

### Step-by-Step Process

#### 1. Regenerate D4D YAMLs (if needed)

If source documents or schema have changed:

```bash
# For all projects using claudecode_agent method
make d4d-agent PROJECT=AI_READI
make d4d-agent PROJECT=CHORUS
make d4d-agent PROJECT=CM4AI
make d4d-agent PROJECT=VOICE
```

#### 2. Generate HTML from YAMLs

```bash
make gen-d4d-html
```

This creates HTML files in `data/d4d_html/concatenated/claudecode_agent/`:
- `{PROJECT}_d4d_human_readable.html` - Human-readable datasheet
- `{PROJECT}_evaluation.html` - Evaluation report

#### 3. Version the HTML Files (AUTOMATED)

Use the new `version-html` target to automatically copy and rename files:

```bash
make version-html VERSION=6
```

This will:
- Copy HTML files from `data/d4d_html/concatenated/claudecode_agent/`
- Rename to versioned format: `D4D_-_{PROJECT}_v6_*.html`
- Place in `src/html/output/` directory
- Create both human-readable and evaluation HTML for all 4 projects

**Example output:**
```
Creating v6 HTML files from claudecode_agent output...
  Versioning AI_READI...
    ✓ Created D4D_-_AI_READI_v6_human_readable.html
    ✓ Created D4D_-_AI_READI_v6_evaluation.html
  Versioning CHORUS...
    ✓ Created D4D_-_CHORUS_v6_human_readable.html
    ✓ Created D4D_-_CHORUS_v6_evaluation.html
  Versioning CM4AI...
    ✓ Created D4D_-_CM4AI_v6_human_readable.html
    ✓ Created D4D_-_CM4AI_v6_evaluation.html
  Versioning VOICE...
    ✓ Created D4D_-_VOICE_v6_human_readable.html
    ✓ Created D4D_-_VOICE_v6_evaluation.html

✅ v6 HTML files created in src/html/output/
```

#### 4. Review Versioned Files

Manually review the generated files in `src/html/output/`:

```bash
ls -lh src/html/output/D4D_-_*_v6_*.html
```

Check for:
- File sizes are reasonable (30-80KB typical)
- Both human_readable and evaluation files for each project
- HTML renders correctly in browser

#### 5. Deploy to GitHub Pages

```bash
make gendoc
```

This copies versioned files to `docs/html_output/` for GitHub Pages deployment.

#### 6. Commit and Push

```bash
git add src/html/output/D4D_-_*_v6_*.html
git add docs/html_output/D4D_-_*_v6_*.html
git add data/d4d_concatenated/claudecode_agent/*.yaml  # If YAMLs changed
git commit -m "Add v6 D4D datasheets"
git push
```

#### 7. Verify Deployment

After GitHub Pages builds (2-5 minutes), verify the new version is accessible:

- https://bridge2ai.github.io/data-sheets-schema/html_output/D4D_-_AI-READI_v6_human_readable.html
- https://bridge2ai.github.io/data-sheets-schema/html_output/D4D_-_CHORUS_v6_human_readable.html
- https://bridge2ai.github.io/data-sheets-schema/html_output/D4D_-_CM4AI_v6_human_readable.html
- https://bridge2ai.github.io/data-sheets-schema/html_output/D4D_-_VOICE_v6_human_readable.html

## File Naming Convention

### Unversioned (Generated)

Located in `data/d4d_html/concatenated/claudecode_agent/`:
- `{PROJECT}_d4d_human_readable.html` - Human-readable datasheet
- `{PROJECT}_evaluation.html` - Evaluation report with quality metrics

### Versioned (Deployed)

Located in `src/html/output/` and `docs/html_output/`:
- `D4D_-_{PROJECT}_v{N}_human_readable.html` - Versioned human-readable datasheet
- `D4D_-_{PROJECT}_v{N}_evaluation.html` - Versioned evaluation report

**Naming Pattern**: `D4D_-_{PROJECT}_v{VERSION}_{TYPE}.html`

Where:
- `{PROJECT}`: AI-READI, CHORUS, CM4AI, or VOICE (note hyphen in AI-READI)
- `{VERSION}`: Integer version number (5, 6, 7, etc.)
- `{TYPE}`: `human_readable` or `evaluation`

## Version History

| Version | Date | Method | Changes |
|---------|------|--------|---------|
| v5 | 2024-12-18 | claudecode_agent | Current version with comprehensive evaluation metrics |
| v4 | 2024-11 | claudecode | Standardized naming, improved structure |
| v3 | 2024-10 | curated | Original FAIRHub/PhysioNet/Dataverse-specific variants |

## Maintaining Previous Versions

**All versions are preserved** in `src/html/output/` and `docs/html_output/`. This allows:
- Version comparison and auditing
- Rollback if needed
- Historical reference
- Citation stability (users can cite specific versions)

To remove old versions (if needed):
```bash
# Remove v4 files
rm src/html/output/D4D_-_*_v4_*.html
rm docs/html_output/D4D_-_*_v4_*.html
```

**Recommendation**: Keep at least the last 2-3 versions published.

## Troubleshooting

### Missing HTML Files

If `make version-html` reports missing files:

```
⚠️  Missing: VOICE_d4d_human_readable.html
```

**Solution**: Regenerate HTML first:
```bash
make gen-d4d-html
```

### Validation Errors

Before creating a new version, validate all YAMLs:

```bash
make validate-d4d-all GENERATOR=claudecode_agent
```

Fix any validation errors before proceeding.

### File Size Anomalies

Typical file sizes:
- Human-readable: 30-50KB (VOICE may be larger at ~70KB)
- Evaluation: 30-80KB

If files are unexpectedly small (<10KB) or large (>200KB), investigate:
```bash
wc -l src/html/output/D4D_-_*_v6_*.html
```

## Advanced: Manual Versioning (Legacy)

If automation fails, you can version manually:

```bash
VERSION=6
for project in AI_READI CHORUS CM4AI VOICE; do
  cp data/d4d_html/concatenated/claudecode_agent/${project}_d4d_human_readable.html \
     src/html/output/D4D_-_${project}_v${VERSION}_human_readable.html

  cp data/d4d_html/concatenated/claudecode_agent/${project}_evaluation.html \
     src/html/output/D4D_-_${project}_v${VERSION}_evaluation.html
done
```

Note: The hyphen in `AI-READI` matches the project naming convention.

## Related Documentation

- [D4D Pipeline Documentation](../notes/D4D_PIPELINE.md) - Complete pipeline overview
- [Critical Paths Plan](/.claude/plans/streamed-painting-catmull.md) - Detailed path documentation
- [CLAUDE.md](../CLAUDE.md) - D4D pipeline section for full workflow

## Questions?

If you encounter issues with versioning:
1. Check `make data-status` to verify pipeline state
2. Validate YAMLs with `make validate-d4d-all`
3. Review HTML generation logs from `make gen-d4d-html`
4. Consult the critical paths plan for complete pipeline flow
