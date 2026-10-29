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

- `.txt`, `.md`, `.json` and `.html` must be strict UTF-8. Their bundle sections preserve lexical contents, including BOM, whitespace, JSON formatting and HTML markup. JSON is not reserialized; HTML is not rendered or stripped. Links and scripts are not fetched or executed. The shared renderer uses the captured bundle bytes and adds canonical chunk markers; source-section hashes remain available.
- `.pdf` contributes offline text extraction from all pages, using the reviewed pdfminer.six version (currently `20221105`). The actual installed converter version is checked and recorded. Encrypted PDFs, extraction failures and PDFs with no extractable text refuse. Images, OCR and complete layout reconstruction are outside this text-only contract.

Other formats, symlinks and nonregular members refuse. There is no Latin-1 fallback, automatic format preference, hidden-file omission or silent truncation. An empty directory, or one with no non-whitespace document text, refuses. The prepared bundle must fit the byte ceiling in [assistant-generation-limits.json](assistant-generation-limits.json). Oversized bundles refuse as a whole. Preparation success does not establish provider context fit or generation success.

**Source provenance.** Each attempt retains an input manifest: the source commit, every relative source path and raw SHA256/size, text/converter policy, exact section byte ranges and hashes, and final bundle SHA256/size. This ingestion manifest is distinct from the chunk manifest used by the generation protocol. The adapter builds that chunk manifest from the actual prepared bundle and pins both in the attempt evidence. Original input files remain unchanged.

The assistant's version 2 framing marks every physical member with a canonical source boundary. Embedded `FILE:/PATH:` text can subdivide that member but cannot absorb the next file. The captured scope maps chunks back to physical input members; an embedded label is not independent proof of a file's origin.

**External-source policy.** All assistant inputs use the explicit `neutral` profile and no study source manifest. A directory's name does not grant it study-specific vocabulary, source rankings or dataset facts. The generation scope names the supplied input directory; unspecified release information stays unknown, and document ordering does not assert a scientific authority ranking. These attempts use a pending diagnostic receipt floor. They are candidate datasheets, not calibrated study results or authorization for a final generation campaign.

**Where the directory must be.** The workflow looks for it in the version of the repository it checks out for the event:

- a request in an issue, or in a comment on an issue or in a pull request's conversation: the default branch;
- a request in a pull request description, or in a review comment on its changes: the pull request's merge commit, so a pull request that adds the directory can request it in its own description;
- a manual run of the workflow: the branch it is run on.

The directory name must start with an ASCII letter or digit and hold only ASCII letters, digits, `_`, `.` and `-`, because the workflow passes it to shell commands. A request that names a directory that is not there, or one whose name breaks this rule, logs "no request" with the reason and gets no reply.

### Edits and manual runs

Editing unrelated prose, moving a request line, or changing only its handle case or whitespace does not submit the same parsed request again. On an edited event, the workflow compares the before and after bodies with the same trusted parser and current input-directory view. It proceeds only when the after text has a valid request for a different dataset, or the before text had no valid request. Edits without a body change are skipped; malformed previous-body data stops the gate. Removing or hiding a request does not run generation.

A manual dispatch authorizes the person who starts it. It first uses the issue or PR body if that body holds a valid parsed request. Otherwise it reads every page of conversation comments and selects the newest valid request in API creation order. Quoted, fenced, hidden or otherwise invalid mentions do not hide an older valid request, and handle case follows the same rules as on events. Editing an old comment does not move it ahead of a newer comment. PR review-thread comments are not part of this manual conversation search.

This check suppresses unrelated body edits; it is not a persistent history of every past run. Separate new comments and explicit manual dispatches may request generation again. Every accepted attempt has a unique GitHub run ID and attempt number. A rerun creates new evidence rather than overwriting an earlier run.

### What the Assistant Does

1. **Prepares** every supported document in the requested repository input directory
2. **Records** the source files, conversions and bundle hashes; it does not fetch linked resources
3. **Registers** the exact shared prompt, schema, bundle, scope, provider and execution limits before generation
4. **Generates** through the existing shared API pipeline, including receipts, derived core, typed audit and reconciliation
5. **Validates** full and core YAML against the captured schema and creates a pull request with the complete attempt evidence in `data/sheets_d4dassistant/`
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

New attempts use `data/sheets_d4dassistant/attempts/{dataset}/{label}/`; historical flat outputs remain unchanged. The attempt contains the registered input authority and an `outputs/` directory with `{dataset}_d4d.yaml`, `{dataset}_d4d_core.yaml`, `{dataset}_reconciliation.md`, `{dataset}_provenance.yaml` and the runner's receipts, audit, usage and phase evidence. The PR body identifies the attempt and original workflow run. Evidence paths in registrations retain their original execution identities; copying an artifact does not make it a new executable registration.

The workflow attempts to upload the complete available attempt on success or failure, including hidden runner state. Its reply distinguishes a successful upload from missing artifact evidence. Runner loss or a failed upload can prevent retention. Failed or incomplete attempts do not create a datasheet PR. GitHub artifact retention is finite; successful PRs also preserve the evidence in Git. Download failed-attempt evidence before its artifact expires if it must be retained longer.

If generation and validation passed but publication failed, use GitHub's **Re-run failed jobs** to retry publication with the original generation artifact. The publisher reuses a pushed branch only when its complete tree and parent match the captured attempt, and reuses an existing PR with the same head commit. Conflicting branches refuse without force-pushing. Generated PRs explicitly target the original request's trusted base branch; a request on a topic-targeted PR does not publish that topic branch's commits into the default branch.

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

The allow-list, request parser and generation code come from one immutable trusted commit: the PR's base SHA for pull-request descriptions and review comments, or the resolved default-branch SHA for other events and manual dispatch. Input directories come from a separate event-selected checkout, so a PR can add documents without supplying executable generation code. The trusted parser runs in Python isolated mode without site initialization. Missing or invalid trusted gate files stop the gate; a PR introducing the parser cannot use its own copy before the base branch has it. Generation receives the provider key but no publication token. A separate job publishes the validated artifacts.

## Technical Details

- **Protocol**: [Registered shared generation v1](../docs/shared-generation-api-v1.md): `generic_v10`, renderer 25, API playbook 2 and receipt completion 2. The workflow explicitly selects this protocol; it does not inherit the legacy CLI default.
- **Prompt agreement**: The assistant uses the ordinary API renderer and registration contract. Equivalent registered inputs produce the same scientific prompt. Native generation shares the selected scientific assets but has a separate runtime adapter and acceptance requirements; this assistant repair does not establish native readiness.
- **Schema**: Uses the full/core LinkML schemas and complete import closures from the same trusted code commit, captured and hashed for the attempt. The existing schema synchronization preflight refuses stale merged products. A moving branch cannot change the schema midway through a run.
- **Provider**: CBORG, explicitly selected, with the existing API model configuration. The shared contract's runtime label `Claude API (direct)` describes the API execution mode; the registration separately records the CBORG provider and endpoint. No fallback to Anthropic occurs.
- **Validation**: Runs `linkml-validate` for both `Dataset` and `CoreDataset` before publication, in addition to the runner's existing completion checks.
- **Workflow**: `.github/workflows/d4d-agent.yml` defines input preparation, generation, validation, PR creation and the final status comment

The old [create](workflows/d4d_assistant_create.md) and [edit](workflows/d4d_assistant_edit.md) instructions are separate legacy interactive instruments. The GitHub workflow loads neither. Their web-fetch/MCP/edit capabilities and old defaults do not describe this workflow. They remain intact for the interactive playbooks that explicitly select them; use the registered protocol above when prompt comparability is required.

## Maintainer configuration and recovery

Provide the repository Actions secret `CBORG_API_KEY` for the selected CBORG route, and `PAT_FOR_PR` for publication. The final status reply uses the workflow's scoped GitHub token. Never put key values in issues, registrations, run evidence or committed configuration. The publication token needs access to create branches and pull requests in this repository. The existing controller allow-list still applies.

[assistant-generation-limits.json](assistant-generation-limits.json) specifies assistant admission ceilings: a 2,000,000-byte bundle, 200,000-token receipt/audit context ceilings, and bounded request, worker, output and aggregate audit allowances. These are operational limits, not measured provider capacity, a scientific coverage target or a total dollar budget. Under `shared_generation_version=1`, the shared runner sets `full`, `reconcile_full` and the report family (report, report regate and report-after-repair) output caps to 128,000 tokens. The D-C decision (2026-10-23) raised the report family and `reconcile_full` from 96,000; `full` and retry accounting are unchanged. Larger inputs can refuse; do not truncate them to fit or silently relax limits after a failed paid attempt.

After deploying reviewed code and configuring the key, manually dispatch the workflow against an existing authorized synthetic request, such as issue [#5050](https://github.com/bridge2ai/data-sheets-schema/issues/5050). Confirm generation, both validations, evidence upload, the resulting PR and the final reply. A green skipped run or offline fixture test does not establish live authentication or generation success. The earlier run [38945203508](https://github.com/bridge2ai/data-sheets-schema/actions/runs/38945203508) reached the legacy Anthropic client and failed with `401 invalid x-api-key`; it is retained as historical failure evidence.

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
