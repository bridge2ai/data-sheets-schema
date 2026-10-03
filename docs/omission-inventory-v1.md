# Offline source-chunk omission inventory

`python -m data_sheets_schema.audit_omissions` prepares a source-first review
request and checks saved JSON responses for #4260, under #2930/#3336. It makes no
model calls. It does not execute generation, reconcile records, alter receipts,
change an audit's terminal state, or claim that an omission was established.

The new `omission_inventory_v1` policy, response schema and context schema live
in `src/data_sheets_schema/omission_inventory_v1/`. Their SHA256 pins are checked
on preparation. Historical audit grammars, renderer instructions, generation
prompts, API policy v1, receipt instruments and registrations are unchanged.
This protocol is not accepted automatically by their readers.

Provide exact selected inputs: a full Dataset record, its bundle and canonical
chunk manifest, its receipt and an explicitly selected schema. The schema and
all local transitive imports are captured once; uncaptured remote imports are
refused. Induced classes and slots include nested Software keys. The complete
original record and every canonical chunk are supplied without lexical filtering
or truncation. Receipt entries marked `nothing_relevant`, `redundant_with`,
`duplicate_of`, or missing from the receipt still receive an inventory row.
Malformed/duplicate/unknown receipt chunk identities are refused; the receipt
must name this bundle. Existing receipt judgments are context, not exemptions.

Context is caller-authored strict JSON, for example:

```json
{
  "format": "omission_context_v1",
  "root_class": "Dataset",
  "scopes": [
    {"owner": "", "referent": "Example release", "release": null,
     "scope": "The released data described by the declared documents."}
  ],
  "source_policy": {"priority": ["release.txt", "methods.txt"],
                    "basis": "Explicit caller declaration"},
  "vocabulary": {}
}
```

No project name, profile, release or source priority is inferred. A null release
means unknown, not the latest release. Supply exact source-priority/naming and
scope declarations in `source_policy`; the checker pins their bytes but does not
certify their correctness or independence. Never place held-out diagnoses,
prior-arm records or ground truth in this context. Required `values_from`
vocabularies must be supplied explicitly under their names. The root scope is
mandatory. Additional scope owners must be distinct existing typed mappings.
A nested resource needs its own owner scope; root scope is not inherited.

```bash
python -m data_sheets_schema.audit_omissions \
  --record /tmp/inputs/full.yaml --receipt /tmp/inputs/receipt.yaml \
  --bundle /tmp/inputs/bundle.txt --manifest /tmp/inputs/chunks.yaml \
  --schema /tmp/inputs/selected-schema.yaml --context /tmp/inputs/context.json \
  --max-output-tokens 12000 --output /tmp/omission-request.json
```

The illustrative cap is not calibrated or recommended. It is recorded, not
checked against a provider context window. The output is a transport-neutral
envelope: request identity, policy, complete record, source chunks, captured
schema, context, input hashes and response schema. It is not an executable API
request. Input files are limited to 8 MB each, captured schema closure to 16 MB,
response to 8 MB, nesting to 64 and parsed node count to 200,000. The complete
request defaults to a 32 MB bound, configurable by `--max-request-bytes`.
Exceeding any limit refuses preparation; no partial inventory is returned.

Each response identifies the exact `request_sha256`, gives one row per chunk and
uses `omission` with nonempty candidates or `no_omission` with none. Both require
a reason. An omission candidate has a globally unique local id, `kind: omission`,
source filename, contiguous quotation, `missing_information`, `scope_basis`, and
`target: {owner: "", slot_chain: ["preprocessing_strategies", "used_software",
"version"]}`. The slot chain names schema declarations, not a populated JSON
Pointer. It can describe an absent value without inventing a list index. The
owner must exist and have caller-supplied scope. Each slot is checked against its
owning induced class, including inlining/cardinality and unsupported conditional
constraints. Chains cannot traverse scalar/reference values or inherit root
scope across a nested Dataset. Unknown fields, ambiguous containers and schema
transitions are refused rather than guessed. Full-record schema validation is
a separate check.

To check a saved response, repeat the same input arguments with
`--request /tmp/omission-request.json --response /tmp/answer.json` and a new
`--output /tmp/omission-check.json`. The recaptured request must match the saved
one exactly, including input/schema/context/policy bytes and limits. Output paths
must be new: existing files, symlinks and hard links are refused. The checker
writes a report and exits 1 for incomplete/invalid responses; input/preparation
errors exit 2. No input is edited. The Python `prepare(...)` result instead
retains an immutable captured request, so later ambient schema edits cannot
change its checks.

`protocol_complete` means the deterministic contract passed: correct request,
chunk accounting, schema targets and quotations. Quotes use the existing
source-assertion rule: contiguous text after whitespace folding, with case and
punctuation retained. Ellipses do not join passages. The bundle preamble cannot
provide factual evidence. `scientific_support`, `novelty` and `exhaustive_recall`
always remain `unverified`, including when every chunk says no_omission. Counts
are explicitly declared candidates/statuses, never independent quality scores.

The policy instructs representation-neutral lineage, actual data-file variables,
software versions stated as used for the declared dataset/activity, source-defined
non-entity granularity and role-sensitive rosters. Those are instructions with
synthetic contract tests, not a semantic classifier or empirical validation.
For example, an exactly quoted companion-study version can pass quotation and
target checks while still being scientifically ineligible. A fact represented
elsewhere in prose can still be wrongly nominated. Independent review is needed.

The [typed offline audit consumer](typed-audit-offline.md) supplies the explicit
versioned grammar, saved-response assembly and independent terminal checks.
The [checked typed-audit report consumer](typed-audit-reporting.md) exports
explicitly selected checked assemblies as JSON or CSV, retaining declared
findings, candidates and their lineage. The standalone
[typed audit Figure 7](typed-audit-figure.md) plots those checked assemblies by
declared finding kind, with untyped findings and separate candidate counts.
The protected historical keyword figure and its outputs remain unchanged.
These counts do not establish scientific support or recall, and the offline
consumers do not deliver omission findings to live generation or reconciliation.
Follow-up work remains in #2930/#3336/#2921: integrated generation delivery,
reconciliation routing, approved observation/hit rules, registered
comparator/predictions and independently reviewed empirical canaries.

The separate [registered receipt-completion runtime](receipt-completion-runtime.md)
implements execution and shared coverage-policy gates for explicitly selected
API renderer-8 conditions. It fills receipts for existing populated values;
it is not source-first omission generation. #2926 retains owner-selected
registration inputs, calibrated thresholds and separately authorized pilots.
#2605/#2714 and all historical pins remain held/unchanged. These offline tools
neither authorize paid runs nor close those parent issues.
