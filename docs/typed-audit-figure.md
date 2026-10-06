# Typed audit Figure 7

The standalone `scripts/figures/fig07_typed_audits.py` renders Figure 7 from
explicitly selected `typed_audit_assembly_v1` files. It reuses the
[checked typed report](typed-audit-reporting.md) before plotting. It does not
classify prose, score records, discover cohorts or change the protected
historical keyword Figure 7, its inputs or its outputs.

Use the repository development environment, which already includes matplotlib:

```sh
PYTHONPATH=src poetry run python scripts/figures/fig07_typed_audits.py \
  --assembly /actual/path/first-assembly.json \
  --assembly /actual/path/second-assembly.json \
  --output-dir /new/path/typed-figure
```

Choose actual complete raw assembly files; these illustrative paths are not
bundled data. The destination directory must not exist. No model, provider,
authentication, native agent or scoring process runs. Plotting imports lazily;
a missing dev dependency causes refusal, not an automatic installation.

## Selection and acceptance

Repeated `--assembly` arguments define the order. Literal file spellings,
absolute/resolved paths, raw byte hashes and canonical assembly identities are
retained separately. A filename does not establish a project, condition or
model identity. The shared report refuses duplicate canonical assemblies,
including a second filename or different JSON whitespace. Distinct assemblies
can still repeat facts and are not assumed to be independent observations.

The consumer reads regular files into immutable captures, then calls
`typed_audit_report.build_report` once. Its existing checker reconstructs the
complete assembly, exact requests/responses, captured source/schema closure,
omission coverage, audit, candidate dispositions and lineage. Saved acceptance
flags, edited reports and bare audits are not authority. Any invalid selection
refuses the entire figure. Captured schema/source files are never reopened for
validation; absent or changed historical files cannot change captured authority.

Existing limits remain: at most 64 assemblies, 320,000,000 selected bytes,
160,000,000 bytes per assembly and the shared byte/node/depth limits. Excess
refuses without truncating rows. The new figure has no implicit subset or
scientific grouping. Rows follow caller order and display selection index plus
canonical hash prefix; full identities are in JSON/CSV.

## Count units and outputs

The left panel counts final findings once by declared kind, including omission.
A missing kind stays **untyped**, even if the finding's prose repeatedly says
"omission". All current protocol kinds plus untyped have explicit count rows,
including zero. The right panel counts retained and dropped omission candidates.
These are different units: one final finding linked to two retained candidates
adds one finding and two candidates. Zero-finding and dropped-only assemblies
remain visible. Counts do not establish scientific support, applicability,
novelty, exhaustive recall or quality improvement.

The fresh output directory contains:

- `fig07_typed_audits.svg`: aligned finding-kind and candidate-disposition panels.
- `checked_audits.json`: the exact canonical, reconstructed base report.
- `checked_audits.csv`: the unchanged base writer's long-form export, preserving
  assembly, final-finding and candidate rows with all source/evidence lineage.
- `finding_counts.csv`: one row per assembly and kind, with explicit finding unit
  and audit-declared/untyped basis, including zeros.
- `candidate_counts.csv`: one row per assembly with declared, retained and dropped
  candidate counts, explicitly labeled with their own unit.
- `manifest.json`: complete state, checked-payload hash, raw selection/file
  identities, consumer source hashes, canonical identities, limitations and
  exact artifact byte counts/SHA256 values.

Tables join on selection index and canonical assembly hash. The base export also
preserves raw hashes, packet/request/response identities, final-finding ordinals,
full findings and candidate linkage. All displayed values come from the same
captured checked payload. The base report's existing limitation that it does not
itself integrate fig07 remains unchanged: `checked_audits.*` are that base export;
this separate consumer adds the SVG and count tables. Existing reporting APIs
and default output bytes are preserved.

## Publication boundary

The package API is `typed_audit_figure.prepare(paths)` followed by
`publish(prepared, output_dir)`. The prepared report is immutable; returning a
parsed copy for inspection cannot edit the prepared bytes. Rendering never
rebuilds from a saved report or reinterprets mutable selected inputs. Integrity
reads recheck raw selected files and consumer source identities before and after
rendering and before the completion manifest; they do not derive new plot values.
These are local consistency checks, not authentication or a lock against an
arbitrary concurrent external writer.

The tool renders privately, reserves a fresh directory, creates artifacts
exclusively, verifies written bytes and writes the complete manifest last.
Existing directories/files, symlinks, input aliases and named captured schema
paths (including absent paths and their ancestors) refuse. Partial failures are
retained without a complete manifest; inspect them and select a different fresh
destination. The tool never removes or replaces a caller's output. Exit 0 means
publication completed; exit 2 indicates a refused input or failed publication.

This is the standalone software consumer in
[#4340](https://github.com/bridge2ai/data-sheets-schema/issues/4340).
It does not close #2930/#3336 or select their v9 versus v8 comparator: actual
generation/reconciliation integration, the common condition decision, new
prompt/renderer registration, pre-run predictions and independently reviewed
empirical canaries remain separate. Synthetic engineering proofs are not
scientific labels or a paid execution authorization.

Completion publication uses a shared helper whose exact source is captured in
publication metadata. The hidden `.figure-completion.pending` entry is retained
for diagnosis and is never a completion marker. Its data stream is closed and
read back before an exclusive link creates the fixed completion name. That link
remains provisional until source, artifact and directory checks finish. If an
observed precommit failure occurs, the helper invalidates its owned inode through
a held descriptor, even in a displaced directory; it does not unlink a pathname
that another writer could replace. Other outputs and replacement winners are
preserved. An empty final marker is a failed publication. Failed invalidation is
reported explicitly as uncertified cleanup, chained to the original error.

After commitment, an operating-system error closing a bookkeeping descriptor is
reported separately on stderr and does not turn the completed publication into
a failed return. Data-stream close errors remain publication failures. If writing and closing
both fail, the first write error remains primary and the close error is its
explicit cause. These
bounded checks do not promise crash or power-loss recovery, atomic visibility to
concurrent readers, or protection against future external mutation. Select a new
fresh directory after a failed attempt; there is no automatic retry or cleanup.
