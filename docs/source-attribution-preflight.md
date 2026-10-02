# Draft source-attribution preflight

A final report can accidentally use registered source IDs such as
`project_documentation` where its source review requires a document filename
such as `protocol.txt`. The direct-arm canary in #2427 encountered this at its
terminal evidence check. The read-only preflight identifies this error while a
report is still a draft:

```bash
d4d review source-attribution-preflight \
  --report draft_reconciliation.md \
  --record final_full.yaml \
  --bundle source_bundle.txt \
  --chunk-manifest source_bundle_chunks.yaml \
  --protocol-version 5 \
  --source-manifest selected_sources.yaml --project EXAMPLE
```

The equivalent module entry point is
`python -m data_sheets_schema.source_attribution_preflight`, with the same
arguments. Both commands print JSON to stdout and write no files. Exit status
0 means this preflight completed without findings; 1 means findings; 2 means
inputs could not be checked. Select protocol 3–7 explicitly. The source
manifest and project are optional together for protocols 5–7; without them the
preflight identifies invalid filenames but does not guess which strings are
registered IDs. It never discovers an ambient source manifest.

`attributed_to` takes distinct exact `source` filenames from the selected chunk
manifest, or `[]` when the clause explicitly credits no document. It never
takes a `source_id` merely because that ID occurs in the source manifest.
Source IDs belong in the separately typed registered-provenance assertions.
Provenance-only clauses require `attributed_to: []`. A filename that happens to
have the same spelling as a source ID remains a filename if it occurs in this
bundle.

For a known ID, a diagnostic names the received ID and its registered filename.
A filename outside the selected bundle is explicitly ineligible; it is not
proposed as a valid replacement. Diagnostics locate each attribution by review
row, claim, and array item, so multiple mistakes within one value are all
visible. Unknown filenames, duplicates and malformed attribution arrays are
also reported. Review each attribution against its clause and evidence. The
preflight does not translate IDs, rewrite the report, or establish that the
clause correctly credits that document.

The command reads each supplied input into a byte snapshot and records SHA256
identities for the report, final full record, bundle, chunk manifest, and
optional source manifest. It verifies the chunk manifest against the bundle
and runs the existing final `source_review` checker unchanged, preserving its
coverage, exact-record binding, quotation, status and attribution rules. Its
result is included under `source_review`; the more detailed vocabulary
explanations are supplementary `attribution_diagnostics`.

A pass is **not terminal evidence admission**. Report-wide assertions,
relationship-removal obligations, controller history, and scientific support
are outside this command's assurance. Every result includes
`terminal_evidence_required: true`; semantic support still requires independent
review. A report or input change invalidates the old snapshot result and needs
a new preflight and the unchanged terminal check.

## Registration boundary

This helper does not change historical evidence protocol texts, renderer
requests, source-review instruments, terminal gates, or existing registrations.
Existing controlled native/direct attempts do not automatically permit this
new command. A failed terminal check or controller stop remains terminal;
this helper does not authorize resuming the stopped #2427 canary.

A future condition that allows preflight feedback must register the exact
command, implementation and input identities, draft stage, permitted feedback,
and bounded correction policy before launch. Preserve the first draft, failed
preflight and each corrected draft in the attempt history. Restrict correction
to the declared draft policy; a diagnostic is not permission to alter records,
source evidence, prior audits, or receipt history. The corrected final bytes
still undergo every registered terminal check. Such controller admission and
a measured canary remain separate work; this offline implementation supplies
neither a paid executor nor empirical validation.
