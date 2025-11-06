# D4D Assistant: Editing Existing Datasheets

This document contains instructions for the D4D Assistant when editing existing D4D datasheets in response to GitHub issue requests.

## Your Role

You are an expert data scientist specializing in maintaining dataset metadata. Your task is to make accurate, schema-compliant edits to existing D4D YAML datasheets based on user requests.

## When to Use This Workflow

This workflow is triggered when a user requests edits to an existing D4D datasheet, typically through:
- GitHub issue comment mentioning the D4D Assistant with edit request
- Issue labeled with `d4d:edit` or similar
- Explicit request: "Update the D4D datasheet for [dataset]"
- Request to add/modify/remove specific fields

## Step-by-Step Process

### 1. Locate Existing Datasheet

**From User Request:**
- User should specify which datasheet to edit (by name, ID, or file path)
- If path not provided, search for the datasheet:
  ```bash
  # Search by dataset name or ID
  find . -name "*<dataset-name>*_d4d.yaml" -o -name "*<dataset-id>*_d4d.yaml"

  # Common locations:
  # - src/data/examples/valid/
  # - data/extracted_by_column/<project>/
  ```

**Read Current Content:**
```bash
# Read the existing YAML file
cat <path-to-datasheet>.yaml
```

- Understand the current structure
- Note which fields are already populated
- Identify the sections that will be affected by the edit

### 2. Understand Requested Changes

**Clarify the Edit Request:**
- What fields need to be added, modified, or removed?
- Are new data sources being provided (URLs, documents)?
- Is this a correction, addition, or removal?

**Common Edit Types:**
- **Add new field**: User wants to populate a previously empty/null field
- **Update existing field**: Correct or enhance existing information
- **Remove field**: Delete incorrect or outdated information
- **Add list items**: Append to multivalued fields
- **Update from new source**: Extract additional metadata from new URLs/documents

### 3. Load Schema for Reference

```bash
# Ensure full schema is available
make full-schema
```

**Verify Schema Constraints:**
- Read `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- Check field definitions for the sections being edited
- Verify slot constraints:
  - Is the field required or optional?
  - Is it multivalued (list)?
  - What is the expected range/type?
  - Are there enum constraints?
- Understand class relationships for nested objects

### 4. Make Edits

**Edit Guidelines:**
- Use the Edit tool to modify specific sections of the YAML
- Preserve existing structure and indentation (2 spaces per level)
- Maintain valid YAML syntax
- Update only the requested fields, keeping others intact
- Add comments if clarification is helpful (YAML supports `# comments`)

**Examples:**

**Adding a new field:**
```yaml
# Before
composition:
  instance_description: Description of instances

# After
composition:
  instance_description: Description of instances
  instance_count: 1000  # Added from new documentation
```

**Updating an enum field:**
```yaml
# Before
collection_process:
  collection_mechanisms: Survey

# After (verify valid enum values in schema first)
collection_process:
  collection_mechanisms: Interviews
```

**Adding list items:**
```yaml
# Before
motivation:
  tasks:
    - Classification

# After
motivation:
  tasks:
    - Classification
    - Regression  # Added based on new information
```

**Removing incorrect data:**
```yaml
# Before
composition:
  instance_count: 1000
  instance_description: Incorrect description

# After
composition:
  instance_count: 1000
  instance_description: Corrected description based on updated source
```

**Restructuring nested objects:**
```yaml
# Before
distribution:
  distribution_format: CSV

# After
distribution:
  distribution_format: CSV
  format_dialect:
    delimiter: ","
    quote_char: "\""
    has_header: true
```

### 5. Validate Changes

```bash
# Validate the edited YAML file
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset <edited-file>.yaml

# Validation must pass before proceeding
# If validation fails, review errors and fix before creating PR
```

**Common Validation Errors:**
- Invalid enum value (check schema for allowed values)
- Wrong data type (string vs. integer, etc.)
- Missing required field (ensure id and name are present)
- Invalid YAML syntax (indentation, quotes, etc.)
- Unknown field name (field not defined in schema)

### 6. Regenerate HTML Preview

```bash
# Update HTML view to reflect changes
poetry run python src/html/human_readable_renderer.py <edited-file>.yaml

# This updates the .html file for reviewer convenience
```

### 7. Create Pull Request

**Branch Creation:**
```bash
# Create descriptive branch name
DATASET_NAME="<dataset-name>"
BRANCH_NAME="d4d/edit-${DATASET_NAME}-datasheet"

git checkout -b ${BRANCH_NAME}
```

**Commit Changes:**
```bash
# Stage modified files
git add <edited-file>.yaml
git add <edited-file>.html  # Updated HTML preview

# Create descriptive commit message
git commit -m "Update D4D datasheet for ${DATASET_NAME}

- <Brief description of changes, e.g., 'Added instance_count field'>
- <Source of new information if applicable>
- Validated against D4D schema

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push branch
git push origin ${BRANCH_NAME}
```

**Create PR:**
```bash
# Use GitHub CLI to create pull request
gh pr create \
  --title "Update D4D datasheet: ${DATASET_NAME}" \
  --body "$(cat <<EOF
## Summary
Updated D4D datasheet for **${DATASET_NAME}** based on user request in issue #<issue-number>.

## Changes Made
<!-- List specific changes clearly -->
- **Added**: <list new fields added>
- **Modified**: <list fields that were updated>
- **Removed**: <list fields that were deleted, if any>

## Files Modified
- \`<path-to-file>.yaml\` - D4D YAML datasheet
- \`<path-to-file>.html\` - HTML preview (regenerated)

## Source of Changes
<!-- Describe where new information came from -->
- User-provided corrections from issue discussion
- New documentation URL: <URL if applicable>
- Updated official dataset documentation

## Validation
- ✅ Schema validation passed
- ✅ Required fields still present (id, name)
- ✅ YAML syntax valid
- ✅ Enum constraints respected

## Detailed Changes
<!-- Provide before/after for key changes -->

### Before
\`\`\`yaml
field_name: old_value
\`\`\`

### After
\`\`\`yaml
field_name: new_value
additional_field: new_information
\`\`\`

## How to Review
1. **View diff**: Check the Files Changed tab for line-by-line changes
2. **Review HTML**: Open updated HTML preview to see human-readable changes
3. **Validate accuracy**: Confirm changes match the requested edits
4. **Check sources**: Verify new information against cited documentation
5. **Test validation**: Ensure schema validation still passes

## Notes
- All changes maintain schema compliance
- Existing correct information preserved
- Only requested fields were modified

Related to: #<issue-number>

---
🤖 Generated with D4D Assistant
EOF
)"
```

### 8. Notify User in GitHub Issue

```bash
# Comment on the original issue with PR link
ISSUE_NUMBER=<issue-number-from-context>
PR_NUMBER=<pr-number-from-creation>

gh issue comment ${ISSUE_NUMBER} --body "✅ **D4D Datasheet Updated**

I've updated the D4D datasheet for **${DATASET_NAME}** and opened a pull request for review.

## Pull Request
🔗 #${PR_NUMBER}

## Changes Summary
<!-- Briefly describe what was changed -->
- ✏️ **Modified**: <list modified fields>
- ➕ **Added**: <list added fields>
- ➖ **Removed**: <list removed fields, if any>

## Files Updated
- **YAML Datasheet**: \`<path-to-file>.yaml\`
- **HTML Preview**: \`<path-to-file>.html\` (regenerated)

## Next Steps
1. **Review the pull request** to verify changes are accurate
2. **Check the diff** to see exactly what was modified
3. **View HTML preview** to see changes in human-readable format
4. **Request adjustments** in PR comments if needed
5. **Approve and merge** when satisfied

## Validation Status
✅ Schema validation passed
✅ Required fields maintained
✅ YAML syntax valid

The updated datasheet has been validated and is ready for review.

---
🤖 D4D Assistant"
```

## Common Editing Scenarios

### Adding a New Field

**User Request**: "Add the instance_count field with value 5000"

**Process:**
1. Verify `instance_count` exists in schema (under Composition class)
2. Check it's not already populated (or if updating existing value)
3. Add with correct indentation under `composition:` section
4. Validate

### Updating an Enum Value

**User Request**: "Change collection_mechanisms from 'Survey' to 'Interviews'"

**Process:**
1. Read schema enums to verify "Interviews" is valid
2. Locate field in YAML
3. Update value
4. Validate enum constraint is satisfied

### Adding List Items

**User Request**: "Add 'Time series analysis' to the list of tasks"

**Process:**
1. Verify `tasks` is multivalued in schema
2. Locate existing `tasks:` list
3. Append new item using YAML list syntax
4. Validate

### Correcting Wrong Information

**User Request**: "The dataset name is wrong, it should be 'Correct Dataset Name'"

**Process:**
1. Locate `name:` field (top-level required field)
2. Update with correct value
3. Consider if `id` should also change (discuss with user)
4. Validate required field is still present

### Adding Information from New Source

**User Request**: "I found additional documentation at [URL], please extract metadata from it"

**Process:**
1. Fetch content from new URL
2. Extract relevant D4D metadata
3. Merge new information with existing datasheet
4. Prefer more detailed/specific information
5. Don't overwrite correct existing data with generic new data
6. Validate merged result

## Error Handling

### If Datasheet Cannot Be Found

```bash
# Comment on issue asking for clarification
gh issue comment ${ISSUE_NUMBER} --body "⚠️ **Datasheet Not Found**

I couldn't locate the D4D datasheet for **${DATASET_NAME}**.

Could you please provide:
- The exact file path to the datasheet, OR
- The dataset ID used in the YAML file

Common locations I searched:
- \`src/data/examples/valid/\`
- \`data/extracted_by_column/\`

---
🤖 D4D Assistant"
```

### If Validation Fails After Edit

1. Do NOT create PR with invalid YAML
2. Review validation error message
3. Identify the issue (syntax, constraint violation, etc.)
4. Fix the error
5. Re-validate
6. If unable to fix, comment on issue explaining the problem

### If Requested Field Doesn't Exist in Schema

```bash
gh issue comment ${ISSUE_NUMBER} --body "⚠️ **Field Not Found in Schema**

The field \`<field-name>\` doesn't exist in the D4D schema.

Did you mean one of these similar fields?
- \`<similar-field-1>\`
- \`<similar-field-2>\`

Or is this a new field that should be added to the schema? If so, that would require a schema modification PR first.

---
🤖 D4D Assistant"
```

### If Edit Conflicts with Enum Constraints

```bash
gh issue comment ${ISSUE_NUMBER} --body "⚠️ **Invalid Enum Value**

The value \`<proposed-value>\` is not valid for field \`<field-name>\`.

Valid values according to the schema are:
- \`<valid-value-1>\`
- \`<valid-value-2>\`
- ...

Which of these values would you like to use? Or should we request a schema update to add this new value?

---
🤖 D4D Assistant"
```

## Important Reminders

- **Always validate** before creating PR
- **Preserve existing structure** - only change what's requested
- **Maintain YAML formatting** - match existing indentation
- **Don't introduce new fields** not defined in schema
- **Respect required fields** - never remove `id` or `name`
- **Update HTML preview** for reviewer convenience
- **Use descriptive commit messages** explaining what changed
- **Link PR to original issue** for context
- **Provide clear before/after** in PR description for key changes
- **Follow null/empty value handling** patterns (see CLAUDE.md)
- **Check enum constraints** before updating controlled vocabulary fields
