# D4D AI Assistant

This repository has an AI assistant (`@d4dassistant`) that can automatically generate D4D (Datasheets for Datasets) YAML files from dataset documentation.

## How to Use

### Request D4D Generation

Authorized users (listed in `.github/ai-controllers.json`) can mention `@d4dassistant` in GitHub issues to request D4D generation:

```markdown
@d4dassistant Please create a D4D for this dataset: https://example.com/dataset-page

Additional context: This dataset contains medical imaging data for cancer research...
```

### What the Assistant Does

1. **Analyzes** your dataset description and any provided URLs
2. **Fetches** documentation from web pages, PDFs, or repositories
3. **Generates** a valid D4D YAML file conforming to the LinkML schema
4. **Validates** the YAML against the schema
5. **Creates** a pull request with the D4D file in `html-demos/user_d4ds/`
6. **Comments** on your issue with a link to the PR

### Example Requests

**With URL:**
```markdown
@d4dassistant Create a D4D for the Bridge2AI VOICE dataset

URL: https://physionet.org/content/b2ai-voice/
This is a voice biomarker dataset for health research.
```

**With description only:**
```markdown
@d4dassistant Generate a D4D for my diabetes study dataset

Dataset name: T2D Longitudinal Study
Description: 5-year longitudinal study of 1000 Type 2 diabetes patients
Format: CSV files with clinical measurements and lab results
License: CC-BY-4.0
```

**With GitHub repository:**
```markdown
@d4dassistant Create D4D from this repo: https://github.com/org/dataset-repo

The README has all the dataset details.
```

## What Information to Provide

The more information you provide, the better the D4D will be. Useful information includes:

- **URLs**: Dataset landing pages, documentation, PDFs, GitHub repos
- **Dataset name**: Short and descriptive
- **Description**: What the dataset contains and why it exists
- **Creators**: Who created/maintains the dataset
- **Size**: Number of instances, file size
- **Format**: CSV, JSON, Parquet, etc.
- **License**: How the data can be used
- **Collection details**: How and when data was gathered
- **Use cases**: What tasks it's intended for

## What Gets Generated

The assistant creates a YAML file following the D4D schema with sections like:

- **Motivation**: Why the dataset was created
- **Composition**: What it contains (instances, splits, etc.)
- **Collection**: How data was gathered
- **Preprocessing**: Data cleaning steps
- **Uses**: Recommended and discouraged applications
- **Distribution**: Access information and licensing
- **Maintenance**: Who maintains it and how to get support

## File Location

Generated D4D files are saved to: `html-demos/user_d4ds/{dataset_name}_d4d.yaml`

Each filename includes a timestamp or unique identifier to avoid conflicts.

## Reviewing the Generated D4D

Once the PR is created:

1. Review the generated YAML file
2. Check that metadata is accurate
3. Request changes if needed (comment on the PR)
4. Merge when satisfied

The assistant can update the D4D based on your feedback - just comment on the PR with your requested changes.

## Authorization

To add users who can invoke the assistant, edit `.github/ai-controllers.json`:

```json
["username1", "username2", "username3"]
```

Only authorized users can trigger the assistant by mentioning `@d4dassistant`.

## Technical Details

- **Agent**: Powered by Claude Code via `dragon-ai-agent/run-goose-obo` GitHub Action
- **Schema**: Uses LinkML schema from `src/data_sheets_schema/schema/`
- **Validation**: Runs `make test-examples` to ensure schema compliance
- **Examples**: References `src/data/examples/valid/` for guidance

## Troubleshooting

**Assistant didn't respond:**
- Check that you're in the authorized users list
- Ensure you mentioned `@d4dassistant` (not `@d4d-assistant` or similar)
- Check GitHub Actions logs for errors

**Generated D4D is incomplete:**
- Provide more information in a follow-up comment
- Share additional URLs or documentation
- The assistant can update the D4D based on new info

**Validation errors:**
- The assistant should fix these automatically
- If the PR has validation errors, comment with details
- The assistant will update the PR

## Support

For issues or questions:
- Open a GitHub issue
- Tag authorized users for assistance
- Check `.goosehints` file for assistant instructions
