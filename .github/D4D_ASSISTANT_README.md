# D4D AI Assistant

This repository has an AI assistant (`@d4dassistant`) that can automatically generate D4D (Datasheets for Datasets) YAML files from dataset documentation.

## How to Use

### Request D4D Generation

Authorized users (listed in `.github/ai-controllers.json`) request a datasheet with one line in an issue, a pull request description or a comment. That line must:

- start with the assistant's handle (shown above), at the very start of the line;
- continue with a space and the name of one directory under `data/sheets_d4dassistant/inputs/`, spelled exactly as the directory is, and nothing else;
- start a paragraph: be the first line, or follow a blank line.

The workflow generates the datasheet for that directory from the documents in it; the rest of the text is not read. Put a new dataset's documents under `data/sheets_d4dassistant/inputs/<name>/` first.

Nothing else is a request (#4108): not the handle in a sentence, in a code span or code block, in a quote (`>`) or an HTML comment, and not the handle followed by anything but one input directory name. For those the workflow logs "no request" and does nothing.

### What the Assistant Does

1. **Analyzes** your dataset description and any provided URLs
2. **Fetches** documentation from web pages, PDFs, or repositories
3. **Generates** a valid D4D YAML file conforming to the LinkML schema
4. **Validates** the YAML against the schema
5. **Creates** a pull request with the D4D file in `html-demos/user_d4ds/`
6. **Comments** on your issue with a link to the PR

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

- **Agent**: Four-phase generation via `d4d api run` (`src/data_sheets_schema/api_runner.py`), run directly in the workflow. Previously used the `dragon-ai-agent/run-claude-obo` action, which no longer exists — see issue #172.
- **Schema**: Uses LinkML schema from `src/data_sheets_schema/schema/`
- **Validation**: Runs `make test-examples` to ensure schema compliance
- **Examples**: References `src/data/examples/valid/` for guidance

## Troubleshooting

**Assistant didn't respond:**
- Check that you're in the authorized users list
- Ensure you mentioned `@d4dassistant` (not `@d4d-assistant` or similar)
- Check that the request line has exactly the form described above; the "Read the request" step of the workflow run logs why a text holds no request
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
