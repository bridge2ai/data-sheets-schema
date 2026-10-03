# Reporting checked typed audits

`python -m data_sheets_schema.typed_audit_report` exports caller-selected
`typed_audit_assembly_v1` files as JSON or CSV. This is the reporting prerequisite
in #4328 for #2930/#3336; it does not change the retained fig07 script, register a
generation condition or establish scientific recall. Legacy bare audits and
prose-derived categories are outside this consumer.

```bash
python -m data_sheets_schema.typed_audit_report \
  --assembly /path/to/first-assembly.json \
  --assembly /path/to/second-assembly.json \
  --format json --output /new/path/typed-audits.json
```

Use `--format csv` and a different fresh destination for CSV. Inputs are selected
explicitly and retain caller order. There is no directory scan, inferred method,
project or cohort, or cross-assembly quality aggregate. Repeating one canonical
assembly is refused even if a different filename or JSON whitespace was used.
Distinct assemblies may still repeat facts; selection does not imply independent
observations. Up to 64 assemblies and 320,000,000 total raw bytes are accepted,
subject also to the existing per-assembly byte, node and depth bounds.

Each input is read once and parsed with the existing strict bounded loader.
`typed_audit.check` reconstructs the packet, exact requests, responses, audit,
candidate dispositions, source checks and complete assembly from captured bytes.
Only after successful exact comparison are rows extracted from that same parsed
object. Saved `passed`, counts and lineage are not independently trusted. Invalid
inputs refuse the whole report; there is no silently omitted failed row. Captured
schema/source authorities are not reopened from current filesystem paths.

JSON contains an ordered `assemblies` list. Every entry records its exact source
file spelling, raw SHA256 and byte count, canonical assembly and packet hashes,
all captured input and schema identities, omission-policy/schema pins, exact raw
audit and saved/inner response identities, request hashes and complete lineage.
Raw payload bytes remain in the selected assembly, not duplicated in the report.
Hashes identify content and declared associations, not provider authentication.

Per-assembly counts keep findings, candidates, retained candidates and dropped
candidates separate. Several candidates can be retained in one finding. Finding
rows retain zero-based final ordinal, original finding/evidence, exact lineage,
and `classification_basis: audit_declared_kind` when a kind is present. Otherwise
the basis is `untyped` and `declared_kind` is null, regardless of prose. The kind
vocabulary is the existing typed protocol's vocabulary; there is no mapping to
legacy figure categories.

CSV is long form. Each assembly has an `assembly` row, including all-negative or
dropped-only audits, followed by `finding` and `candidate` detail rows. Join on
`selection_index` and `assembly_sha256`. Counts and full identity/lineage JSON
cells appear only on assembly rows, so summing a count column does not multiply
it by the number of detail rows. Candidate rows preserve disposition evidence,
source quote/chunk and schema target, candidate/disposition hashes, and linked
finding ordinal (empty for a dropped candidate). Finding rows retain their exact
finding JSON and finding lineage. Nested cells are compact JSON, not Python repr.

Scientific support, applicability, novelty and exhaustive recall remain
unverified. A mechanically accepted declared omission is not an established
omission or evidence of improved recall. The synthetic tests are engineering
checks, not empirical observations or human-adjudicated ground truth.

All outputs require fresh paths. Existing files, hardlinks and symlinks
(including dangling links) are refused. Named captured schema authority paths
are protected even when the old files are absent. The complete serialized report
is staged, flushed and published with exclusive creation; a competing existing
destination wins without being overwritten. Exit 0 means publication succeeded;
exit 2 means invalid input, failed reconstruction, duplicate selection or an I/O
refusal. Historical report APIs/defaults, stored outputs and figures are unchanged.
