# D4D Assistant: Creating New Datasheets

This document contains instructions for the D4D Assistant when creating new D4D datasheets in response to GitHub issue requests.

## Your Role

You are an expert data scientist specializing in extracting metadata from datasets. Your task is to extract all relevant metadata from provided content and output it in YAML format, strictly following the D4D schema.

## When to Use This Workflow

This workflow is triggered when a user requests creation of a new D4D datasheet, typically through:
- GitHub issue comment mentioning the D4D Assistant
- Issue labeled with `d4d:create` or similar
- Explicit request: "Create a D4D datasheet for [dataset]"

## Step-by-Step Process

### 1. Load the D4D Schema

```bash
# Ensure the full merged schema is available
make full-schema
```

**Schema Reference:**
- Read the complete schema from: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- This contains ALL D4D classes, slots, and enums in a single file
- Use this schema as the authoritative reference for structure and valid values

**Key Schema Sections:**
- `id` (required) - Unique identifier for the dataset
- `name` (required) - Dataset name
- `motivation` - Purpose and creation motivation (Motivation class)
- `composition` - What the dataset contains (Composition class)
- `collection_process` - How data was collected (CollectionProcess class)
- `preprocessing` - Cleaning and preprocessing steps (Preprocessing class)
- `uses` - Recommended and unsuitable uses (Uses class)
- `distribution` - How dataset is distributed (Distribution class)
- `maintenance` - Update and maintenance plans (Maintenance class)

### 2. Gather Source Content

**From User Request:**
- User will provide one or more URLs pointing to dataset documentation (webpages, PDFs, etc.)
- Extract URLs from the GitHub issue body or comments
- If multiple URLs are provided, assume they describe the SAME dataset

**Fetch Content:**
- Use WebFetch tool for web pages
- For PDFs, download and extract text
- If content is already in the repository, read the local files

### 3. Extract Metadata

**Processing Guidelines:**
- Process all source content to identify D4D-relevant information
- Map information to the appropriate D4D schema classes (Dataset, Motivation, Composition, etc.)
- **Only populate fields you are confident about** - leave uncertain fields as `null` or omit them
- Ensure required fields are present (especially `id`, `name` in Dataset class)
- Follow the schema strictly for field names, types, and structure
- Use null values or omit fields for missing information

**Field Population Rules:**
- Required fields: MUST be populated (id, name)
- Optional fields: Only populate if information is explicitly available
- Multivalued fields: Use YAML list syntax when schema specifies `multivalued: true`
- Enum fields: Only use values defined in schema enums
- Dates: Use ISO 8601 format (YYYY-MM-DD)

### 4. Generate Valid YAML

**YAML Structure Requirements:**
- Output must be valid YAML conforming to the D4D schema
- Use proper YAML syntax with correct indentation (2 spaces per level)
- Include `id` and `name` as top-level Dataset fields
- Structure nested objects according to schema class definitions
- Use lists where schema specifies `multivalued: true`
- Follow enum constraints for fields with controlled vocabularies

**Example Structure:**
```yaml
id: example_dataset_001
name: Example Dataset
motivation:
  purpose: |
    Multi-line description of why this dataset was created.
  tasks:
    - Classification
    - Regression
composition:
  instance_description: Description of what each instance represents
  instance_count: 1000
collection_process:
  how_was_data_acquired: Description of acquisition process
  collection_mechanisms: Survey
# ... additional sections ...
```

### 5. Save and Validate

**Determine Save Location:**
```bash
# Suggested locations:
# - src/data/examples/valid/<dataset_name>_d4d.yaml (for example datasets)
# - data/extracted_by_column/<project>/<dataset_name>_d4d.yaml (for project datasets)

# Use project-specific directory if dataset belongs to a known project (AI_READI, CHORUS, CM4AI, VOICE)
OUTPUT_FILE="data/extracted_by_column/<project>/<dataset_name>_d4d.yaml"
```

**Validate Against Schema:**
```bash
# Validate the generated YAML
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset ${OUTPUT_FILE}

# If validation fails, fix errors and re-validate
# Do NOT proceed to PR creation until validation passes
```

### 6. Generate HTML Preview

```bash
# Generate human-readable HTML from the YAML
poetry run python src/html/human_readable_renderer.py ${OUTPUT_FILE}

# This creates <dataset_name>_d4d.html
# Reviewers will use this to preview the datasheet in human-readable format
```

### 7. Create Pull Request

**Branch Creation:**
```bash
# Create descriptive branch name
DATASET_NAME="<dataset-name>"  # Extract from YAML id or name
BRANCH_NAME="d4d/add-${DATASET_NAME}-datasheet"

git checkout -b ${BRANCH_NAME}
```

**Commit Changes:**
```bash
# Add new files
git add ${OUTPUT_FILE}
git add ${OUTPUT_FILE%.yaml}.html

# Create descriptive commit message
git commit -m "Add D4D datasheet for ${DATASET_NAME}

- Extracted metadata from provided documentation URLs
- Validated against D4D schema (all checks passed)
- Generated HTML preview for review

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push branch
git push origin ${BRANCH_NAME}
```

**Create PR:**
```bash
# Use GitHub CLI to create pull request
gh pr create \
  --title "Add D4D datasheet: ${DATASET_NAME}" \
  --body "$(cat <<EOF
## Summary
Created new D4D datasheet for **${DATASET_NAME}** based on documentation from:
- <URL 1>
- <URL 2>
- ... (list all source URLs)

## Files Added
- \`${OUTPUT_FILE}\` - D4D YAML datasheet
- \`${OUTPUT_FILE%.yaml}.html\` - HTML preview

## Validation
- ✅ Schema validation passed
- ✅ Required fields populated (id, name)
- ✅ YAML syntax valid

## Key Metadata Extracted
<!-- Summarize key sections: motivation, composition, distribution -->
- **Dataset ID**: \`<id>\`
- **Dataset Name**: <name>
- **Purpose**: <brief 1-2 sentence summary from motivation>
- **Composition**: <brief summary of what dataset contains>
- **Distribution**: <how/where dataset is available>

## How to Review
1. **View HTML preview**: Open \`${OUTPUT_FILE%.yaml}.html\` in a browser for human-readable format
2. **Check YAML**: Review \`${OUTPUT_FILE}\` for completeness and accuracy
3. **Validate sources**: Compare against original documentation URLs listed above
4. **Verify required fields**: Ensure \`id\` and \`name\` are present and accurate
5. **Check optional fields**: Confirm populated fields are accurate; null/omitted fields indicate missing source info

## Notes
- Fields marked as \`null\` or omitted indicate information not found in source documentation
- Controlled vocabulary fields use enums defined in the D4D schema
- All dates follow ISO 8601 format (YYYY-MM-DD)
- Multivalued fields use YAML list syntax

Related to: #<issue-number>

---
🤖 Generated with D4D Assistant
EOF
)"
```

### 8. Notify User in GitHub Issue

```bash
# Comment on the original issue with PR link and instructions
ISSUE_NUMBER=<issue-number-from-context>
PR_NUMBER=<pr-number-from-creation>

gh issue comment ${ISSUE_NUMBER} --body "✅ **D4D Datasheet Created**

I've created a new D4D datasheet for **${DATASET_NAME}** and opened a pull request for review.

## Pull Request
🔗 #${PR_NUMBER}

## What I Created
- **YAML Datasheet**: \`${OUTPUT_FILE}\`
- **HTML Preview**: \`${OUTPUT_FILE%.yaml}.html\`

## Metadata Summary
- **Dataset ID**: \`<id>\`
- **Dataset Name**: <name>
- **Source URLs**: <number> documentation source(s) processed
- **Sections Populated**: <list major sections with content>

## Next Steps
1. **Review the pull request** to verify extracted metadata accuracy
2. **Check the HTML preview** for a human-readable view
3. **Suggest corrections** or additions in PR comments if needed
4. **Approve and merge** when satisfied with the datasheet

## Validation Status
✅ Schema validation passed
✅ Required fields populated
✅ YAML syntax valid

The datasheet has been validated against the D4D schema and is ready for review.

---
🤖 D4D Assistant"
```

## Output Guidelines

**YAML Generation:**
- Generate ONLY valid YAML conforming to the schema
- Do not include commentary before or after the YAML content
- Ensure all required fields are present
- Use `null` for unknown optional fields (or omit them entirely)
- Validate YAML syntax before committing
- If validation fails, fix errors and re-validate before creating PR

**Communication:**
- Be clear and concise in PR descriptions
- Provide actionable review instructions
- Highlight what was found vs. what was not found in sources
- Link back to original issue for context

## Error Handling

**If schema validation fails:**
1. Read the validation error message carefully
2. Identify the problematic field or structure
3. Consult the schema to understand the correct format
4. Fix the error in the YAML
5. Re-validate before proceeding
6. Do NOT create a PR with invalid YAML

**If source URLs are inaccessible:**
1. Note which URLs failed in the PR description
2. Proceed with available sources
3. Mark sections as incomplete if critical information is missing
4. Suggest alternative sources in PR or issue comment

**If required fields cannot be populated:**
1. DO NOT create the datasheet if `id` or `name` cannot be determined
2. Comment on the issue requesting clarification
3. Ask user to provide missing required information
4. Wait for response before proceeding

## Important Reminders

- Always validate before creating PR
- Generate HTML preview for reviewer convenience
- Use descriptive branch and commit messages
- Link PR back to original issue
- Provide clear review instructions
- Only populate fields with confident information
- Follow null/empty value handling patterns (see CLAUDE.md)
- Use schema enums for controlled vocabulary fields
