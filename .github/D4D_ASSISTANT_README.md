# D4D AI Assistant

This repository has an AI assistant (`@d4dassistant`) that can automatically generate D4D (Datasheets for Datasets) YAML files from dataset documentation.

## How to Use

### Request D4D Generation

Authorized users (listed in `.github/ai-controllers.json`) request a datasheet with one line in an issue, a pull request description or a comment. That line must:

- start with the assistant's handle (shown above), at the very start of the line;
- continue with a space and the name of one directory under `data/sheets_d4dassistant/inputs/`, spelled exactly as the directory is, and nothing else;
- stand alone: have a blank line, or the start or end of the text, both before it and after it.

Nothing else is a request (#4108): not the handle in a sentence, in a code span or code block, in a quote (`>`) or an HTML comment, and not the handle followed by anything but one input directory name. Nor is a request line read after a code fence or HTML block whose end the workflow cannot place (one opened on a list marker, for example), or after HTML that leaves something open (an unclosed comment or tag, or an element such as `<textarea>`), since the page may hide it. For those the workflow logs "no request" and does nothing. A text whose request lines name different directories holds no request.

**Which files are read.** The workflow prepares every regular file in the selected directory, recursively, including hidden files, in sorted relative-path order. Each named occurrence has its own labeled section; equal contents or equal basenames are not deduplicated. The rest of the request text is not source documentation. Preparation finishes before generation starts; one unsupported, unreadable or failed document stops the run rather than producing a partial bundle.

Supported filename extensions are case-insensitive:

- `.txt`, `.md`, `.json` and `.html` must be strict UTF-8. Their bundle sections preserve lexical contents, including BOM, whitespace, JSON formatting and HTML markup. JSON is not reserialized; HTML is not rendered or stripped. Links and scripts are not fetched or executed. Before provider submission, the existing API reader converts CRLF and lone CR to LF and adds its existing prompt headers; the bundle's raw section hashes remain available.
- `.pdf` contributes offline text extraction from all pages, using the reviewed pdfminer.six version (currently `20221105`). The actual installed converter version is checked and recorded. Encrypted PDFs, extraction failures and PDFs with no extractable text refuse. Images, OCR and complete layout reconstruction are outside this text-only contract.

Other formats, symlinks and nonregular members refuse. There is no Latin-1 fallback, automatic format preference, hidden-file omission or silent truncation. An empty directory, or one with no non-whitespace document text, refuses. The workflow has no aggregate input-size admission cap in this generic route; including all documents can increase billed input, and preparation success does not establish provider context fit or generation success.

**Source provenance.** The generated PR includes `{dataset}_input_manifest.json` alongside the datasheet: the checked-out source commit, every relative source path and raw SHA256/size, text/converter policy, exact section byte ranges and hashes, and final bundle SHA256/size. This is an ingestion manifest, not a scientific coverage judgment or the runner's source/chunk manifest. Original input files remain unchanged. The PR body links the manifest and identifies the complete member count and bundle hash.

**Where the directory must be.** The workflow looks for it in the version of the repository it checks out for the event:

- a request in an issue, or in a comment on an issue or in a pull request's conversation: the default branch;
- a request in a pull request description, or in a review comment on its changes: the pull request's merge commit, so a pull request that adds the directory can request it in its own description;
- a manual run of the workflow: the branch it is run on.

The directory name must start with an ASCII letter or digit and hold only ASCII letters, digits, `_`, `.` and `-`, because the workflow passes it to shell commands. A request that names a directory that is not there, or one whose name breaks this rule, logs "no request" with the reason and gets no reply.

### What the Assistant Does

1. **Prepares** every supported document in the requested repository input directory
2. **Records** the source files, conversions and bundle hashes; it does not fetch linked resources
3. **Generates** a valid D4D YAML file conforming to the LinkML schema
4. **Validates** the YAML against the schema
5. **Creates** a pull request with generated files and the input manifest in `data/sheets_d4dassistant/`
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

Generated D4D files use the existing flat layout in `data/sheets_d4dassistant/`: `{dataset}_d4d.yaml`, `{dataset}_d4d_core.yaml`, `{dataset}_reconciliation.md` and `{dataset}_provenance.yaml`. Complete-input preparation adds `{dataset}_input_manifest.json`; the run label remains timestamped by the workflow.

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

The allow-list and request parser come from one immutable trusted commit: the PR's base SHA for pull-request descriptions and review comments, or the resolved default-branch SHA for other events and manual dispatch. Input directories still come from the event-selected checkout described above, so a PR can add a dataset without changing its authorization rules. The trusted parser runs in Python isolated mode without site initialization. Missing or invalid trusted gate files stop the gate; a PR introducing the parser cannot use its own copy before the base branch has it.

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
- If that log says the name is not an input directory, check that the directory is where the workflow looks for it (see "Where the directory must be" above)
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
