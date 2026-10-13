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

### Edits and manual runs

Editing unrelated prose, moving a request line, or changing only its handle case or whitespace does not submit the same parsed request again. On an edited event, the workflow compares the before and after bodies with the same trusted parser and current input-directory view. It proceeds only when the after text has a valid request for a different dataset, or the before text had no valid request. Edits without a body change are skipped; malformed previous-body data stops the gate. Removing or hiding a request does not run generation.

A manual dispatch authorizes the person who starts it. It first uses the issue or PR body if that body holds a valid parsed request. Otherwise it reads every page of conversation comments and selects the newest valid request in API creation order. Quoted, fenced, hidden or otherwise invalid mentions do not hide an older valid request, and handle case follows the same rules as on events. Editing an old comment does not move it ahead of a newer comment. PR review-thread comments are not part of this manual conversation search.

This check suppresses unrelated body edits; it is not a persistent history of every past run. Separate new comments and explicit manual dispatches may request generation again. The existing run-label and output checks still apply, so a repeat is not a promise that a new run will be accepted.

### What the Assistant Does

1. **Prepares** every supported document in the requested repository input directory
2. **Records** the source files, conversions and bundle hashes; it does not fetch linked resources
3. **Generates** a candidate datasheet through the configured `d4d api run` phases
4. **Validates** the YAML against the schema
5. **Creates** a pull request with generated files and the input manifest in `data/sheets_d4dassistant/`
6. **Comments** on your issue with a link to the PR

## What Information to Provide

Put source documentation in the named repository input directory using the supported formats above, then submit the explicit request line. The issue or comment text selects the directory; additional prose and URLs in that request are not generation inputs. URLs inside source documents remain text references: the workflow does not fetch their contents. To supply a linked document, include its contents as a supported file in the input directory.

Useful source documentation describes the dataset's purpose, contents, creators, size, formats, license, collection methods and intended uses. Schema validation checks structure; a reviewer still needs to check whether the generated statements accurately reflect those documents.

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
3. Review requested corrections and edit the generated files or their source documentation as appropriate
4. Merge when satisfied

Ordinary feedback comments do not instruct the assistant to edit a datasheet. Generating again requires an explicit request under the rules above and remains subject to the existing run/output checks.

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
- **Validation**: Runs `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` on the generated full YAML before opening the PR
- **Workflow**: `.github/workflows/d4d-agent.yml` defines input preparation, generation, validation, PR creation and the final status comment

## Troubleshooting

**Assistant didn't respond:**
- Check that you're in the authorized users list
- Ensure you mentioned `@d4dassistant` (not `@d4d-assistant` or similar)
- Check that the request line has exactly the form described above; the "Read the request" step of the workflow run logs why a text holds no request
- If that log says the name is not an input directory, check that the directory is where the workflow looks for it (see "Where the directory must be" above)
- Check GitHub Actions logs for errors

**Generated D4D is incomplete:**
- Check the input manifest and the source files in the requested directory
- Add missing documentation as supported repository files; follow-up prose and links alone are not ingested
- Review the generated statements and correct the files or make a new explicit request when appropriate

**Validation errors:**
- Inspect the failing validation step and its run log
- A failed generation or validation is reported; the workflow does not automatically repair it or update a PR from feedback
- Correct the relevant source or generated content before requesting another run

## Support

For issues or questions:
- Open a GitHub issue
- Tag authorized users for assistance
- Consult the request rules above and the linked workflow steps in GitHub Actions
